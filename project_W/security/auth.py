import json
from base64 import urlsafe_b64decode
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import project_W.dependencies as dp
from project_W.models.response_data import User

from ..logger import get_logger
from ..models.internal import DecodedAuthTokenData
from ..models.response_data import ErrorResponse, User, UserTypeEnum
from .ldap_deps import lookup_ldap_user_in_db_from_token
from .local_account_deps import lookup_local_user_in_db_from_token
from .local_token import jwt_issuer, validate_local_auth_token
from .oidc_deps import lookup_oidc_user_in_db_from_token, validate_oidc_token

logger = get_logger("project-W")

# define all possible HTTP responses here so that they can be included together with the dependency for the docs
auth_dependency_responses: dict[int | str, dict[str, Any]] = {
    401: {
        "model": ErrorResponse,
        "headers": {
            "WWW-Authenticate": {
                "type": "string",
            }
        },
        "description": "Validation error of JWT token",
    },
    403: {
        "model": ErrorResponse,
        "headers": {
            "WWW-Authenticate": {
                "type": "string",
            }
        },
        "description": "Token doesn't grand enough permissions",
    },
}

get_token = HTTPBearer(
    bearerFormat="Bearer",
    scheme_name="JWT token (from local account, oidc or ldap auth)",
    description="""
    A valid JWT token returned by one of the following login routes:
    - local account: /local-account/login
    - oidc: /oidc/login/{idp_name}
    - ldap: /ldap/login/{idp_name}
    Which of these are available with what idp's depends on the server configuration
    """,
)


def get_payload_from_token(token: str) -> dict:
    payload = token.split(".")[1]
    payload_padded = payload + "=" * divmod(len(payload), 4)[1]
    payload_decoded = urlsafe_b64decode(payload_padded)
    return json.loads(payload_decoded)


def validate_user(require_verified: bool, require_admin: bool):
    async def user_validation_dep(
        token: Annotated[HTTPAuthorizationCredentials, Depends(get_token)]
    ) -> DecodedAuthTokenData:
        # first check how this token was generated without verifying the signature
        token_payload = get_payload_from_token(token.credentials)
        iss = token_payload.get("iss")
        if iss is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token",
                # can't put scope here because if the issuer is unknown we also don't know which scope might be required
                headers={"WWW-Authenticate": "Bearer"},
            )
        if iss == jwt_issuer:
            token_data = await validate_local_auth_token(
                dp.config, token.credentials, token_payload
            )
        else:
            token_data = await validate_oidc_token(dp.config, token.credentials, iss)

        if require_verified and not token_data.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your email address needs to be verified to access this route. Please click on the link sent to {token_data.email} or request a new confirmation email.",
            )

        if require_admin and not token_data.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return token_data

    return user_validation_dep


def validate_user_and_get_from_db(require_verified: bool, require_admin: bool):
    async def user_lookup_dep(
        user_token_data: Annotated[
            DecodedAuthTokenData, Depends(validate_user(require_verified, require_admin))
        ]
    ) -> User:
        if user_token_data.user_type == UserTypeEnum.LOCAL:
            return await lookup_local_user_in_db_from_token(user_token_data)
        elif user_token_data.user_type == UserTypeEnum.LDAP:
            return await lookup_ldap_user_in_db_from_token(user_token_data)
        elif user_token_data.user_type == UserTypeEnum.OIDC:
            return await lookup_oidc_user_in_db_from_token(user_token_data)
        else:
            raise Exception("Invalid token type encountered!")

    return user_lookup_dep
