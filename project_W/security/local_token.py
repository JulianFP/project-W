from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from pydantic import ValidationError

import project_W.dependencies as dp
from project_W.models.settings import SessionTokenValidated, Settings

from ..logger import get_logger
from ..models.internal import (
    AccountActivationTokenData,
    AuthTokenData,
    DecodedAuthTokenData,
    PasswordResetTokenData,
)

admin_user_scope = "admin"
jwt_issuer = "project-W"
jwt_algorithm = "HS256"

logger = get_logger("project-W")


def create_token(
    data: dict,
    secret_key: SessionTokenValidated,
    expires_delta: timedelta | None = None,  # None means infinite lifetime
):
    data["iss"] = jwt_issuer
    if expires_delta is not None:
        data["exp"] = datetime.now(timezone.utc) + expires_delta

    token = jwt.encode(data, secret_key.root.get_secret_value(), algorithm=jwt_algorithm)
    return token


def validate_token(token: str, secret_key: SessionTokenValidated) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            secret_key.root.get_secret_value(),
            algorithms=[jwt_algorithm],
            issuer=jwt_issuer,
        )
        return payload
    except jwt.InvalidTokenError:
        return None


# this function generates JWT tokens for local as well as LDAP accounts
async def create_auth_token(
    config: Settings,
    data: AuthTokenData,
    user_id: int,
    is_admin: bool = False,
    scopes: list[str] = [],
    infinite_lifetime: bool = False,  # also determines which token secret is used
    name: str | None = None,
) -> str:

    to_encode = {
        **data.model_dump(),
        "scopes": scopes,
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
    else:
        assert name is not None
        second_half_secret = await dp.db.get_new_token_for_user(user_id, name)
        expires_delta = None

    to_encode["token_id"] = second_half_secret.id
    secret_key = SessionTokenValidated.model_validate(
        config.security.local_token.session_secret_key.root.get_secret_value()[:32]
        + second_half_secret.secret
    )
    return create_token(to_encode, secret_key, expires_delta)


def create_account_activation_token(config: Settings, data: AccountActivationTokenData):
    secret_key = config.security.local_token.session_secret_key
    expires_delta = timedelta(days=1)
    return create_token(data.model_dump(), secret_key, expires_delta)


def create_password_reset_token(config: Settings, data: PasswordResetTokenData):
    secret_key = config.security.local_token.session_secret_key
    expires_delta = timedelta(hours=1)
    return create_token(data.model_dump(), secret_key, expires_delta)


# this function validates jwt tokens (for both local and LDAP accounts) and returns the associated users
async def validate_local_auth_token(
    config: Settings, token: str, token_payload: dict
) -> DecodedAuthTokenData:
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
    secret_key = SessionTokenValidated.model_validate(
        config.security.local_token.session_secret_key.root.get_secret_value()[:32]
        + second_half_secret.secret
    )

    payload = validate_token(token, secret_key)
    if payload is None:
        logger.error("Authentication attempt with invalid (possibly expired?) JWT token")
        raise credentials_exception

    # check if the scopes of the token grant the required access rights
    token_scopes = payload.get("scopes", [])
    if admin_user_scope in token_scopes:
        payload["is_admin"] = True
    else:
        payload["is_admin"] = False

    # return queried user
    try:
        return DecodedAuthTokenData.model_validate(payload)
    except ValidationError:
        logger.error("Authentication attempt with JWT token whose data didn't pass validation")
        raise credentials_exception


def validate_account_activation_token(config: Settings, token: str) -> AccountActivationTokenData:
    secret_key = config.security.local_token.session_secret_key
    payload = validate_token(token, secret_key)
    try:
        return AccountActivationTokenData.model_validate(payload)
    except ValidationError:
        logger.error("Account activation attempt with JWT token whose data didn't pass validation")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate account activation token",
        )


def validate_password_reset_token(config: Settings, token: str) -> PasswordResetTokenData:
    secret_key = config.security.local_token.session_secret_key
    payload = validate_token(token, secret_key)
    try:
        return PasswordResetTokenData.model_validate(payload)
    except ValidationError:
        logger.error("Password reset attempt with JWT token whose data didn't pass validation")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate password reset token",
        )
