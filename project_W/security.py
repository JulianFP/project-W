import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import ValidationError

from .database import database_adapter
from .logger import get_logger
from .model import TokenData, UserInDb

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="users/login",
    scopes={"admin": "Has full admin privileges, can read all users data and more!"},
)


class jwt_token_handler:
    """
    Utility class for jwt token stuff
    """

    secret_key: str
    db: database_adapter
    algorithm = "HS256"

    def setup(
        self, database: database_adapter, jwt_secret_key: str = secrets.token_urlsafe(64)
    ) -> None:
        self.secret_key = jwt_secret_key
        self.db = database
        self.logger = get_logger("project-W")

    def create_jwt_token(self, data: dict, expires_delta: timedelta = timedelta(hours=1)):
        print(f"current secret key {self.secret_key}")
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    async def get_current_user(
        self, security_scopes: SecurityScopes, token: Annotated[str, Depends(oauth2_scheme)]
    ) -> UserInDb:
        if security_scopes.scopes:
            authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
        else:
            authenticate_value = "Bearer"
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": authenticate_value},
        )
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            email: str | None = payload.get("sub")
            if email is None:
                self.logger.error(
                    "Authentication attempt with JWT token that doesn't contain a sub field"
                )
                raise credentials_exception
            token_scopes = payload.get("scopes", [])
            token_data = TokenData(scopes=token_scopes, email=email)
        except jwt.InvalidTokenError:
            self.logger.error("Authentication attempt with invalid (possibly expired?) JWT token")
            raise credentials_exception
        except ValidationError:
            self.logger.error(
                "Authentication attempt with JWT token whose data didn't pass validation"
            )
            raise credentials_exception
        user = await self.db.get_user_by_email(token_data.email)
        if user is None:
            self.logger.error(
                "Authentication attempt with JWT token which belongs to a non-existing user"
            )
            raise credentials_exception
        for scope in security_scopes.scopes:
            if scope not in token_data.scopes:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": authenticate_value},
                )
        return user
