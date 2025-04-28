from pydantic import BaseModel, Field

from .base import EmailValidated, UserInDb
from .response_data import TokenSecretInfo, UserTypeEnum


# user models for the database
class LocalUserInDb(UserInDb):
    password_hash: str
    is_admin: bool
    is_verified: bool
    provision_number: int | None


class OidcUserInDb(UserInDb):
    iss: str
    sub: str


class LdapUserInDb(UserInDb):
    provider_name: str
    dn: str


class AccountActivationTokenData(BaseModel):
    old_email: EmailValidated
    new_email: EmailValidated


class PasswordResetTokenData(BaseModel):
    email: EmailValidated


class AuthTokenData(BaseModel):
    user_type: UserTypeEnum
    sub: str
    email: EmailValidated
    is_verified: bool


class DecodedAuthTokenData(AuthTokenData):
    token_id: int | None = None
    is_admin: bool
    iss: str


class TokenSecret(TokenSecretInfo):
    user_id: int
    secret: str = Field(min_length=32, max_length=32)


class LdapUserInfo(BaseModel):
    dn: str
    is_admin: bool
    email: EmailValidated
