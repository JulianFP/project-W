from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

import project_W.dependencies as dp

from ..models.internal import AuthTokenData
from ..models.response_data import ErrorResponse, TokenSecretInfo, User, UserTypeEnum
from ..security.auth import (
    auth_dependency_responses,
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
) -> str:
    """
    Invalidate the local token with the provided id. Doesn't work for OIDC tokens. After calling this route the token with the provided id can't be used anymore.
    """
    await dp.db.delete_token_secret_of_user(current_user.id, token_id)
    return "Success"


@router.delete("/invalidate_all_tokens")
async def invalidate_all_tokens(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ],
) -> str:
    """
    Invalidate all local tokens of the logged in user account. Doesn't work for OIDC tokens. After calling this route all local tokens of the logged in user account won't work anymore.
    """
    await dp.db.delete_all_token_secrets_of_user(int(current_user.id))
    return "Success"


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
    name: Annotated[str, Query(max_length=64)],
) -> str:
    """
    Create a new API token. The main difference between API tokens and the JWT tokens that you get after login is that API tokens never expire. Only create them if necessary and only use a different token for each device/service so that it is easy to invalidate one of them if a device gets compromised. The provided name has the purpose of being able to identify which token belongs to which device/service.THe successfuly response contains the newly created token.
    """
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
    """
    Get a list of all token id's and names currently in use by this account. Temporary tokens created by the login route all share the same id and this id is marked as such. All other id's/names refer to API tokens that the user explicitly created using the get_new_api_token route.
    """
    return await dp.db.get_info_of_all_tokens_of_user(current_user.id)


@router.get("/info")
async def user_info(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ],
) -> User:
    """
    This route returns all information about the currently logged in user. In addition to the information that is encoded in the JWT token itself (which the client could just extract on its own) it also returns information from the database and replaces iss/sub information with the provider name and account type of the user (local/ldap/oidc).
    """
    return current_user


@router.delete("/delete")
async def delete_user(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ],
) -> str:
    """
    Deletes the currently logged in user and all information related to it (like jobs, tokens, etc.)
    """
    await dp.db.delete_user(current_user.id)
    return "Success"
