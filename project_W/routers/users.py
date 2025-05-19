from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

import project_W.dependencies as dp

from ..models.internal import AuthTokenData, DecodedAuthTokenData
from ..models.response_data import ErrorResponse, TokenSecretInfo, User, UserTypeEnum
from ..security.auth import (
    auth_dependency_responses,
    validate_user,
    validate_user_and_get_from_db,
)
from ..security.local_token import create_auth_token

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses=auth_dependency_responses,
)


@router.delete("/invalidate_token")
async def invalidate_token(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ],
    token_id: int,
):
    await dp.db.delete_token_secret_of_user(current_user.id, token_id)


@router.delete("/invalidate_all_tokens")
async def invalidate_all_tokens(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ],
):
    await dp.db.delete_all_token_secrets_of_user(int(current_user.id))


@router.post(
    "/get_new_api_token",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Creation of api tokens is disabled for your identity provider",
        }
    },
)
async def get_new_api_token(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=True, require_admin=False))
    ],
    name: str,
):
    # check if current user is from a provider which allows creation of api tokens
    disabled_exc = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Creation of api tokens is disabled for your account type. Login using a different provider or ask the administrator to enable this.",
    )
    if (
        current_user.user_type == UserTypeEnum.OIDC
        and not dp.config.security.oidc_providers[
            current_user.provider_name
        ].allow_creation_of_api_tokens
    ):
        raise disabled_exc
    if (
        current_user.user_type == UserTypeEnum.LDAP
        and not dp.config.security.ldap_providers[
            current_user.provider_name
        ].allow_creation_of_api_tokens
    ):
        raise disabled_exc
    if (
        current_user.user_type == UserTypeEnum.LOCAL
        and not dp.config.security.local_account.allow_creation_of_api_tokens
    ):
        raise disabled_exc

    data = AuthTokenData(
        user_type=current_user.user_type,
        sub=str(current_user.id),
        email=current_user.email,
        is_verified=current_user.is_verified,
    )
    return await create_auth_token(
        dp.config, data, current_user.id, current_user.is_admin, infinite_lifetime=True, name=name
    )


@router.get("/get_all_token_info")
async def get_all_token_info(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ],
) -> list[TokenSecretInfo]:
    return await dp.db.get_info_of_all_tokens_of_user(current_user.id)


@router.get("/info")
async def token_info(
    current_token: Annotated[
        DecodedAuthTokenData, Depends(validate_user(require_verified=False, require_admin=False))
    ],
) -> DecodedAuthTokenData:
    return current_token


@router.get("/info_db")
async def user_info(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ],
) -> User:
    return current_user


@router.delete("/delete")
async def delete_user(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ],
):
    await dp.db.delete_user(current_user.id)
    return "success!"
