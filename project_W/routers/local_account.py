from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import SecretStr, ValidationError

from project_W.models.base import (
    EmailValidated,
    LocalAccountOperationModeEnum,
    PasswordValidated,
)

from .. import dependencies as dp
from ..models.internal import (
    AccountActivationTokenData,
    AuthTokenData,
    DecodedAuthTokenData,
    PasswordResetTokenData,
)
from ..models.request_data import PasswordResetData, SignupData
from ..models.response_data import ErrorResponse, UserTypeEnum
from ..security.auth import auth_dependency_responses, validate_user
from ..security.local_token import (
    create_account_activation_token,
    create_auth_token,
    create_password_reset_token,
    validate_account_activation_token,
    validate_password_reset_token,
)


async def validate_token_local_not_provisioned(
    current_token: Annotated[
        DecodedAuthTokenData, Depends(validate_user(require_verified=False, require_admin=False))
    ],
) -> DecodedAuthTokenData:
    if current_token.user_type is not UserTypeEnum.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only users who are logged in with a local Project-W account can use this route",
        )

    user = await dp.db.get_local_user_by_email(current_token.email)
    if (user is None) or (user.provision_number is not None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This route cannot be called by the current user because they have been provisioned through the admin config file. Please change any user attributes there instead.",
        )

    return current_token


validate_token_local_not_provisioned_responses = {
    400: {
        "model": ErrorResponse,
        "description": "User is not a local Project-W user or has been provisioned through the config file",
    },
}


# for when users need to confirm their identity with their password
async def validate_token_local_not_provisioned_confirmed(
    password: Annotated[SecretStr, Body()],
    current_token: Annotated[DecodedAuthTokenData, Depends(validate_token_local_not_provisioned)],
) -> DecodedAuthTokenData:
    if not (await dp.db.get_local_user_by_email_checked_password(current_token.email, password)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirmation password invalid",
        )

    return current_token


validate_token_local_not_provisioned_confirmed_responses = {
    403: {
        "model": ErrorResponse,
        "description": "Confirmation password invalid",
    },
} | validate_token_local_not_provisioned_responses


router = APIRouter(
    prefix="/local-account",
    tags=["local-account"],
)


@router.post(
    "/login",
    responses={401: {"model": ErrorResponse, "description": "Authentication was unsuccessful"}},
)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> str:
    """
    Log in to an existing local Project-W account. This is an OAuth2 compliant password request form where the username is the user's email address. A successful response will contain a token that needs to be attached in the authentication header of responses for routes that require the user to be logged in.
    If logging in with an admin account the returned JWT token will not give you admin privileges by default. If you need a token with admin privileges then specify the scope 'admin' during login.
    """
    try:
        email = EmailValidated.model_validate(form_data.username)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided username is not a valid email address",
        )

    user = await dp.db.get_local_user_by_email_checked_password(
        email, SecretStr(form_data.password)
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    data = AuthTokenData(
        user_type=UserTypeEnum.LOCAL,
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
async def signup(data: SignupData, background_tasks: BackgroundTasks) -> str:
    """
    Create a new local Project-W account. The provided email must be valid and the password must adhere to certain criteria (must contain at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total) and the email can't already be in use by another account.
    """
    if dp.config.security.local_account.mode != LocalAccountOperationModeEnum.ENABLED:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Signup of new local accounts is disabled on this server",
        )

    if (
        dp.config.security.local_account.allowed_email_domains
        and data.email.get_domain() not in dp.config.security.local_account.allowed_email_domains
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{data.email.get_domain()}' is not an allowed email domain on this server",
        )

    if (user_id := await dp.db.add_local_user(data.email, data.password, False, False)) is None:
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
async def activate(token: SecretStr) -> str:
    """
    Activate a local Project-W account, meaning validate it's email address. The token was sent to the user on account creation, email address change or when they specifically requested an email with the resend_activation_email route. Only activated users are able to submit transcription jobs and actually use this service.
    """
    payload = validate_account_activation_token(dp.config, token.get_secret_value())
    user = await dp.db.get_local_user_by_email(payload.old_email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No user with email '{payload.old_email.root}' exists",
        )
    if user.is_verified and payload.old_email == payload.new_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email address '{payload.old_email.root}' is already verified",
        )

    await dp.db.verify_local_user(user.id, payload.new_email)

    # invalidate existing tokens because they contain is_verified and email information
    await dp.db.delete_all_token_secrets_of_user(user.id)

    return "Success"


@router.get(
    "/resend_activation_email",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "This user is not a local user or is already activated",
        },
    }
    | validate_token_local_not_provisioned_responses
    | auth_dependency_responses,
)
async def resend_activation_email(
    current_token: Annotated[DecodedAuthTokenData, Depends(validate_token_local_not_provisioned)],
    background_tasks: BackgroundTasks,
) -> str:
    """
    This will resend an activation email to the user like the one the user got when their account was created. Useful if they forgot to click on the link and lost the old email. Can only be requested if the user is not verified yet.
    """
    if current_token.user_type != UserTypeEnum.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not a local Project-W user",
        )
    if current_token.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user is already verified",
        )

    account_activation_token = create_account_activation_token(
        dp.config,
        AccountActivationTokenData(old_email=current_token.email, new_email=current_token.email),
    )
    background_tasks.add_task(
        dp.smtp.send_account_activation_email,
        current_token.email,
        account_activation_token,
        dp.config.client_url,
    )
    return "A new account activation email for this user will be sent shortly"


@router.get(
    "/request_password_reset",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Email invalid",
        },
    },
)
async def request_password_reset(email: str, background_tasks: BackgroundTasks) -> str:
    """
    Requests a password reset email that will be sent to the user containing a link to a password reset page. The provided email address must belong to an existing local Project-W account.
    """
    # cannot have pydantic model as query parameter, so validate email here manually
    try:
        validated_email = EmailValidated.model_validate(email)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provided email is not a valid email address",
        )

    user = await dp.db.get_local_user_by_email(validated_email)
    if (user is not None) and (user.provision_number is None):
        password_reset_token = create_password_reset_token(
            dp.config, PasswordResetTokenData(email=validated_email)
        )
        background_tasks.add_task(
            dp.smtp.send_password_reset_email,
            validated_email,
            password_reset_token,
            dp.config.client_url,
        )

    return f"If a local Project-W account with the address {email} exists then a password reset email will be sent shortly."


@router.post(
    "/reset_password",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Password reset token doesn't match any user",
        },
        401: {"model": ErrorResponse, "description": "Password reset token invalid"},
    },
)
async def reset_password(password_reset: PasswordResetData) -> str:
    """
    Resets the password of an account to the provided password. The token is the one from the password reset email that can be requested with the /request_password_reset route.
    """
    payload = validate_password_reset_token(dp.config, password_reset.token.get_secret_value())
    if not await dp.db.update_local_user_password(payload.email, password_reset.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No local user with the email {payload.email} exists",
        )

    return "Success"


@router.post(
    "/change_user_email",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Email domain not allowed or email already in use",
        },
    }
    | validate_token_local_not_provisioned_confirmed_responses
    | auth_dependency_responses,
)
async def change_user_email(
    new_email: EmailValidated,
    current_token: Annotated[
        DecodedAuthTokenData, Depends(validate_token_local_not_provisioned_confirmed)
    ],
    background_tasks: BackgroundTasks,
) -> str:
    """
    Change the email address of a local Project-W account. This change will only take effect after the user has clicked on the link in the activation email that this route sends to the new email address.
    """
    if (
        dp.config.security.local_account.allowed_email_domains
        and new_email.get_domain() not in dp.config.security.local_account.allowed_email_domains
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{new_email.get_domain()}' is not not an allowed email domain on this server",
        )

    if (await dp.db.get_local_user_by_email(new_email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{new_email.root}' is already in use by another user",
        )

    account_activation_token = create_account_activation_token(
        dp.config, AccountActivationTokenData(old_email=current_token.email, new_email=new_email)
    )
    background_tasks.add_task(
        dp.smtp.send_confirm_email_change_email,
        new_email,
        account_activation_token,
        dp.config.client_url,
    )
    return f"Successfully requested email address change. An email confirmation email will be sent to you shortly. Please click on the link in that email to complete the email changing process."


@router.post(
    "/change_user_password",
    responses=validate_token_local_not_provisioned_confirmed_responses | auth_dependency_responses,
)
async def change_user_password(
    new_password: PasswordValidated,
    current_token: Annotated[
        DecodedAuthTokenData, Depends(validate_token_local_not_provisioned_confirmed)
    ],
) -> str:
    """
    Change the password of a local Project-W account. In contrary to requesting a password reset email this route is authenticated meaning that to use this route the user must still be able to log in into their account, but it changes the password immediately without going through a link in an email first.
    """
    await dp.db.update_local_user_password(current_token.email, new_password)
    return "Successfully updated user password"
