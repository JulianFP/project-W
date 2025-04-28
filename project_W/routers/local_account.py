from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError

from project_W.models.base import EmailValidated
from project_W.models.settings import LocalAccountOperationModeEnum

from .. import dependencies as dp
from ..models.internal import AccountActivationTokenData, AuthTokenData
from ..models.request_data import SignupData, SignupDataVerified
from ..models.response_data import ErrorResponse, User, UserTypeEnum
from ..security.auth import auth_dependency_responses, validate_user_and_get_from_db
from ..security.local_token import (
    create_account_activation_token,
    create_auth_token,
    validate_account_activation_token,
)

router = APIRouter(
    prefix="/local-account",
    tags=["local-account"],
)


@router.post(
    "/login",
    responses={401: {"model": ErrorResponse, "description": "Authentication was unsuccessful"}},
)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    try:
        email = EmailValidated.model_validate(form_data.username)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided username is not a valid email address",
        )

    user = await dp.db.get_local_user_by_email_checked_password(email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    data = AuthTokenData(
        user_type=UserTypeEnum.local,
        sub=str(user.id),
        email=user.email,
        is_verified=user.is_verified,
    )

    return await create_auth_token(dp.config, data, user.id, user.is_admin, form_data.scopes)


@router.post(
    "/signup",
    responses={
        400: {"model": ErrorResponse, "description": "Email or password have invalid syntax"},
        405: {
            "model": ErrorResponse,
            "description": "Signup of new accounts is disabled on this server",
        },
    },
)
async def signup(signup_data: SignupData, background_tasks: BackgroundTasks):
    if dp.config.security.local_account.mode != LocalAccountOperationModeEnum.enabled:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Signup of new local accounts is disabled on this server",
        )

    try:
        data = SignupDataVerified.model_validate(signup_data.model_dump())
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The provided email address is invalid",
        )
    if data.email.domain not in dp.config.security.local_account.allowed_email_domains:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{data.email.domain}' is not not an allowed email domain on this server",
        )

    if (
        user_id := await dp.db.add_local_user(
            data.email, data.password.get_secret_value(), False, False
        )
    ) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-Mail is already in use by another local account",
        )

    account_activation_token = create_account_activation_token(
        dp.config, AccountActivationTokenData(old_email=data.email, new_email=data.email)
    )
    background_tasks.add_task(
        dp.smtp.send_account_activation_email,
        data.email,
        account_activation_token,
        dp.config.client_url,
    )
    return (
        f"Successfully created user with id {user_id}. The activation email will be sent shortly."
    )


@router.post(
    "/activate",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Activation token doesn't match any user, or user has already been activated",
        },
        401: {"model": ErrorResponse, "description": "Activation token invalid"},
    },
)
async def activate(token: str):
    payload = validate_account_activation_token(dp.config, token)
    user = await dp.db.get_local_user_by_email(payload.old_email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No user with email {payload.old_email} exists",
        )
    if user.is_verified and payload.old_email == payload.new_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email address {payload.old_email} is already verified",
        )

    await dp.db.verify_local_user(user.id, payload.new_email)


@router.get(
    "/resend_activation_email",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "This user is not a local user or is already activated",
        },
    }
    | auth_dependency_responses,
)
async def resend_activation_email(
    current_user: Annotated[User, Depends(validate_user_and_get_from_db(require_admin=False))],
    background_tasks: BackgroundTasks,
):
    if current_user.user_type != UserTypeEnum.local:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not a local Project-W user",
        )
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is already verified",
        )

    account_activation_token = create_account_activation_token(
        dp.config,
        AccountActivationTokenData(old_email=current_user.email, new_email=current_user.email),
    )
    background_tasks.add_task(
        dp.smtp.send_account_activation_email,
        current_user.email,
        account_activation_token,
        dp.config.client_url,
    )
    return "A new account activation email for this user will be sent shortly"
