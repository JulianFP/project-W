from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

import project_W.dependencies as dp
from project_W.models.settings import Settings

from ..logger import get_logger
from ..models.internal import DecodedTokenData, TokenData

admin_user_scope = "admin"
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(
    tokenUrl="/auth",
    scopes={
        admin_user_scope: "Admin user, has full administrative privileges, can read data of every user and more!"
    },
)
jwt_issuer = "project-W"
jwt_algorithm = "HS256"

logger = get_logger("project-W")


# this function generates JWT tokens for local as well as LDAP accounts
async def create_jwt_token(
    config: Settings,
    data: TokenData,
    user_id: int,
    is_admin: bool = False,
    scopes: list[str] = [],
    infinite_lifetime: bool = False,  # also determines which token secret is used
    name: str | None = None,
) -> str:

    to_encode = {
        **data.model_dump(),
        "scopes": scopes,
        "iss": jwt_issuer,
    }

    # make sure that we only assign scopes that the user has permissions for (currently only is_admin, can be replaced with attribute set in the future)
    for scope in scopes:
        if scope == admin_user_scope:
            if not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Your user isn't an admin",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="We don't support that token permission scope",
            )

    if not infinite_lifetime:
        # get token secret
        second_half_secret = await dp.db.get_temp_session_token_secret_of_user(user_id)
        if second_half_secret is None:
            raise Exception(f"User with id {user_id} doesn't have a temp session token secret")

        # calculate expiration date
        expires_delta = timedelta(
            minutes=config.security.local_token.session_expiration_time_minutes
        )
        to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    else:
        assert name is not None
        second_half_secret = await dp.db.get_new_token_for_user(user_id, name)

    to_encode["token_id"] = second_half_secret.id
    secret_key = config.security.local_token.session_secret_key + second_half_secret.secret
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=jwt_algorithm)
    return encoded_jwt


# this function validates jwt tokens (for both local and LDAP accounts) and returns the associated users
async def validate_local_token(
    config: Settings, token: Annotated[str, Depends(oauth2_scheme)], token_payload: dict
) -> DecodedTokenData:
    # prepare http exceptions
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # get secret key
    user_id = token_payload.get("sub")
    token_id = token_payload.get("token_id")
    if user_id is None or token_id is None:
        raise credentials_exception

    second_half_secret = await dp.db.get_token_secret_of_user(user_id, token_id)
    if second_half_secret is None:
        raise credentials_exception
    secret_key = config.security.local_token.session_secret_key + second_half_secret.secret

    # validate token by checking its hash value, exp and the existence of all required fields
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[jwt_algorithm],
            issuer=jwt_issuer,
        )
        email: str | None = payload.get("email")
        if email is None:
            logger.error(
                "Authentication attempt with JWT token that doesn't contain an email field"
            )
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
    except jwt.InvalidTokenError:
        logger.error("Authentication attempt with invalid (possibly expired?) JWT token")
        raise credentials_exception
    except ValidationError:
        logger.error("Authentication attempt with JWT token whose data didn't pass validation")
        raise credentials_exception

    # check if the scopes of the token grant the required access rights
    if admin_user_scope in token_scopes:
        payload["is_admin"] = True
    else:
        payload["is_admin"] = False

    # return queried user
    return DecodedTokenData.model_validate(payload)
