from enum import Enum

from pydantic import BaseModel, Field

from .base import AdditionalUserInfo, EmailValidated, InProcessJobBase, UserInDb
from .request_data import JobSettings, RunnerRegisterRequest
from .response_data import TokenSecretInfo, UserTypeEnum


class UserInDbAll(UserInDb, AdditionalUserInfo):
    pass


# user models for the database
class LocalUserInDb(UserInDb):
    password_hash: str
    is_admin: bool
    is_verified: bool
    provision_number: int | None


class LocalUserInDbAll(LocalUserInDb, AdditionalUserInfo):
    pass


class OidcUserInDb(UserInDb):
    iss: str
    sub: str


class OidcUserInDbAll(OidcUserInDb, AdditionalUserInfo):
    pass


class LdapUserInDb(UserInDb):
    provider_name: str
    dn: str


class LdapUserInDbAll(LdapUserInDb, AdditionalUserInfo):
    pass


class RunnerInDb(BaseModel):
    id: int
    token_hash: str


class JobSettingsInDb(BaseModel):
    settings: JobSettings


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


class JobSortKey(str, Enum):
    CREATION_TIME = "creation_time"
    FILENAME = "filename"


class InProcessJob(InProcessJobBase):
    """
    Represents a job that is currently being processed by a runner.
    Instances of this are created as soon as the runner retrieves the
    audio file from the server, and live until the server fully retrieves
    the completed transcript or until the runner fails.
    """

    runner_id: int
    user_id: int


class OnlineRunner(RunnerRegisterRequest):
    """
    Represents one instance of a runner that's currently registered as online. Note
    that this is separate from the Runner class that represents a runner database entry.
    Since job assignments and such don't persist across server restarts, we don't need to
    store them to the DB anyways.
    """

    id: int
    assigned_job_id: int | None = None
    in_process: bool = False
    session_token_hash: str = Field(min_length=43, max_length=43)
