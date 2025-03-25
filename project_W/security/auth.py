import json
from base64 import urlsafe_b64decode
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

import project_W.dependencies as dp
from project_W.models.response_data import User

from ..logger import get_logger
from ..models.internal import DecodedTokenData
from ..models.response_data import User
from .local_account import lookup_local_user_in_db_from_token
from .local_token import jwt_issuer, validate_local_token
from .oidc import lookup_oidc_user_in_db_from_token, validate_oidc_token

logger = get_logger("project-W")


async def get_jwt_token(request: Request) -> str:
    if not (token := request.headers.get("authorization")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )
    else:
        # strip out 'Bearer ' from token string
        return token.split(" ")[1]


def get_payload_from_token(token: str) -> dict:
    payload = token.split(".")[1]
    payload_padded = payload + "=" * divmod(len(payload), 4)[1]
    payload_decoded = urlsafe_b64decode(payload_padded)
    return json.loads(payload_decoded)


def validate_user(require_admin: bool):
    async def user_validation_dep(
        token: Annotated[str, Depends(get_jwt_token)]
    ) -> DecodedTokenData:
        # first check how this token was generated without verifying the signature
        token_payload = get_payload_from_token(token)
        if token_payload.get("iss") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                # can't put scope here because if the issuer is unknown we also don't know which scope might be required
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token_payload.get("iss") == jwt_issuer:
            token_data = await validate_local_token(dp.config, token)
        else:
            token_data = await validate_oidc_token(dp.config, token, token_payload["iss"])

        if require_admin and not token_data.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return token_data

    return user_validation_dep


def validate_user_and_get_from_db(require_admin: bool):
    async def user_lookup_dep(
        user_token_data: Annotated[
            DecodedTokenData, Depends(validate_user(require_admin=require_admin))
        ]
    ) -> User:
        if user_token_data.iss == jwt_issuer:
            return await lookup_local_user_in_db_from_token(user_token_data)
        else:
            return await lookup_oidc_user_in_db_from_token(user_token_data)

    return user_lookup_dep
