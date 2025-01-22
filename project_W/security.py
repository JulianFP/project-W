from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import ValidationError

import project_W.dependencies as dp

from .logger import get_logger
from .model import AuthRequestForm, Token, TokenData, UserInDb

admin_user_scope = "admin"
oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(
    tokenUrl="/auth",
    scopes={
        admin_user_scope: "Admin user, has full administrative privileges, can read data of every user and more!"
    },
)
jwt_algorithm = "HS256"
jwt_issuer = "project-W"
logger = get_logger("project-W")


# this function generates JWT tokens for local accounts as well as LDAP accounts
def create_jwt_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()

    # put issuer in JWT token
    to_encode.update({"iss": jwt_issuer})

    # put expiration date in JWT
    if expires_delta is None:
        expires_delta = timedelta(minutes=dp.config.login_security.session_expiration_time_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, dp.config.login_security.session_secret_key, algorithm=jwt_algorithm
    )
    return encoded_jwt


async def authenticate_user(form_data: AuthRequestForm) -> Token:
    incorrect_credentials_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect username or password",
    )

    ldap_server = form_data.ldap_server
    if ldap_server is None:
        user = await dp.db.get_user_by_email_checked_password(
            form_data.username, form_data.password
        )
        if not user:
            raise incorrect_credentials_exception
    else:
        # TODO: Verify username and password with specified LDAP server instead. Only then query
        email_of_verified_user = ""
        password_of_verified_user = ""
        if email_of_verified_user is None:
            raise incorrect_credentials_exception
        user = await dp.db.get_user_by_email(email_of_verified_user)
        if user is None:
            # TODO: pull permissions from ldap to also create admin users if they have the correct permissions on ldap
            # TODO: ldap users should have their ldap server in the database. Also it doesn't make sense for them to have an is_admin field in the database, make that optional
            await dp.db.add_new_user(
                email_of_verified_user, password_of_verified_user, False, True
            )  # already activated because we trust LDAP as a source

    for scope in form_data.scopes:
        if scope == admin_user_scope:
            user_not_admin_exception = HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your user isn't an admin",
            )
            if ldap_server is None:
                if not user.is_admin:
                    raise user_not_admin_exception
            else:
                # TODO: Check LDAP server for permissions here
                raise user_not_admin_exception
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="We don't support that token permission scope",
            )
    access_token = create_jwt_token(data={"email": user.email, "scopes": form_data.scopes})
    return Token(access_token=access_token, token_type="bearer")


# this function validates jwt tokens and returns the associated users
async def validate_token(
    token: Annotated[str, Depends(oauth2_scheme)], secret_key: str, required_scope: str | None
) -> UserInDb:
    # prepare http exceptions
    if required_scope is None:
        authenticate_value = "Bearer"
    else:
        authenticate_value = f'Bearer scope ="{required_scope}"'

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    permission_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions",
        headers={"WWW-Authenticate": authenticate_value},
    )

    # validate token by checking its hash value, exp and the existence of all required fields
    try:
        logger.info(secret_key)
        payload = jwt.decode(token, secret_key, algorithms=[jwt_algorithm])
        email: str | None = payload.get("email")
        if email is None:
            logger.error(
                "Authentication attempt with JWT token that doesn't contain an email field"
            )
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, email=email)
    except jwt.InvalidTokenError:
        logger.error("Authentication attempt with invalid (possibly expired?) JWT token")
        raise credentials_exception
    except ValidationError:
        logger.error("Authentication attempt with JWT token whose data didn't pass validation")
        raise credentials_exception

    # check if the scopes of the token grant the required access rights
    if required_scope is not None:
        if required_scope not in token_data.scopes:
            raise permission_exception

    # query user associated with token and check if that user even exists
    ldap_server = payload.get("ldap_server")
    if ldap_server:
        # TODO: Query user from LDAP server instead from local database
        user = None
    else:
        user = await dp.db.get_user_by_email(token_data.email)
    if user is None:
        logger.error("Authentication attempt with JWT token which belongs to a non-existing user")
        raise credentials_exception

    # return queried user
    return user


async def validate_normal_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDb:
    # first check how this token was generated without verifying the signature
    issuer_unverified = jwt.decode(token, options={"verify_signature": False}).get("iss")
    if issuer_unverified is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )

    if issuer_unverified == jwt_issuer:
        return await validate_token(token, dp.config.login_security.session_secret_key, None)
    else:
        # TODO: Read required scope for normal user from oidc config in self.login_security_settings and use IdPs public key
        return await validate_token(token, "", "")


async def validate_admin_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDb:
    # first check how this token was generated without verifying the signature
    issuer_unverified = jwt.decode(token, options={"verify_signature": False}).get("iss")
    if issuer_unverified is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )

    if issuer_unverified == jwt_issuer:
        return await validate_token(
            token, dp.config.login_security.session_secret_key, admin_user_scope
        )
    else:
        # TODO: Read required scope for admin user from oidc config in self.login_security_settings and use IdPs public key
        return await validate_token(token, "", "")
