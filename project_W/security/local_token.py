from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

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
def create_jwt_token(
    config: Settings,
    data: TokenData,
    is_admin: bool = False,
    scopes: list[str] = [],
    expires_delta: timedelta | None = None,
) -> str:
    # calculate expiration date
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=config.security.local_token.session_expiration_time_minutes
        )
    expire = datetime.now(timezone.utc) + expires_delta

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

    to_encode = {
        **data.model_dump(),
        "scopes": scopes,
        "iss": jwt_issuer,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        to_encode, config.security.local_token.session_secret_key, algorithm=jwt_algorithm
    )
    return encoded_jwt


# this function validates jwt tokens (for both local and LDAP accounts) and returns the associated users
async def validate_local_token(
    config: Settings, token: Annotated[str, Depends(oauth2_scheme)]
) -> DecodedTokenData:
    # prepare http exceptions
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # validate token by checking its hash value, exp and the existence of all required fields
    try:
        payload = jwt.decode(
            token,
            config.security.local_token.session_secret_key,
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
    print(payload)
    return DecodedTokenData.model_validate(payload)
