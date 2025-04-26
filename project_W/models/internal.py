from pydantic import BaseModel, Field

from .base import UserInDb
from .response_data import TokenSecretInfo, UserTypeEnum


# user models for the database
class LocalUserInDb(UserInDb):
    password_hash: str
    is_admin: bool
    is_verified: bool


class OidcUserInDb(UserInDb):
    iss: str
    sub: str


class LdapUserInDb(UserInDb):
    provider_name: str
    dn: str


class TokenData(BaseModel):
    user_type: UserTypeEnum
    sub: str
    email: str
    is_verified: bool


class DecodedTokenData(TokenData):
    token_id: int | None = None
    is_admin: bool
    iss: str


class TokenSecret(TokenSecretInfo):
    user_id: int
    secret: str = Field(min_length=32, max_length=32)


class LdapUserInfo(BaseModel):
    dn: str
    is_admin: bool
    email: str
