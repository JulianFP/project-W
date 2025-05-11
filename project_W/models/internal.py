from enum import Enum

from pydantic import BaseModel, Field

from .base import EmailValidated, JobBase, UserInDb
from .request_data import RunnerRegisterRequest
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


class RunnerInDb(BaseModel):
    id: int
    token_hash: str


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


class JobInDb(JobBase):
    user_id: int
    job_settings_id: int | None
    audio_oid: int | None
    transcript: str | None


class JobSortKey(str, Enum):
    CREATION_TIME = "creation_time"
    FILENAME = "filename"


class InProcessJob(BaseModel):
    """
    Represents a job that is currently being processed by a runner.
    Instances of this are created as soon as the runner retrieves the
    audio file from the server, and live until the server fully retrieves
    the completed transcript or until the runner fails.
    """

    id: int
    runner_id: int
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    abort: bool = False


class OnlineRunner(RunnerRegisterRequest):
    """
    Represents one instance of a runner that's currently registered as online. Note
    that this is separate from the Runner class that represents a runner database entry.
    Since job assignments and such don't persist across server restarts, we don't need to
    store them to the DB anyways.
    """

    id: int
    assigned_job_id: int | None = None
    in_process_job_id: int | None = None
