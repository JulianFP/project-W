from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from .. import dependencies as dp
from ..models.internal import DecodedTokenData, TokenData
from ..models.response_data import ErrorResponse, User, UserTypeEnum
from .local_token import create_jwt_token

router = APIRouter(
    prefix="/local-account",
    tags=["local-account"],
)


@router.post(
    "/login",
    responses={401: {"model": ErrorResponse, "description": "Authentication was unsuccessful"}},
)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await dp.db.get_local_user_by_email_checked_password(
        form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    data = TokenData(
        user_type=UserTypeEnum.local,
        sub=str(user.id),
        email=user.email,
        is_verified=user.is_verified,
    )

    return await create_jwt_token(dp.config, data, user.id, user.is_admin, form_data.scopes)


async def lookup_local_user_in_db_from_token(user_token_data: DecodedTokenData) -> User:
    local_user = await dp.db.get_local_user_by_email(user_token_data.email)
    if not local_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication successful, but the user was not found in database",
        )
    return User(
        id=local_user.id,
        user_type=UserTypeEnum.local,
        email=local_user.email,
        provider_name="project-W",
        is_admin=local_user.is_admin,
        is_verified=local_user.is_verified,
    )
