from pydantic import BaseModel, Field
from enum import Enum
from project_W_lib.models.base import EmailValidated, UserBase
from project_W_lib.models.response_models import (
    InProcessJobResponse,
    JobAndSettingsResponse,
    JobResponse,
    TokenInfoResponse,
    UserResponse,
)
from project_W_lib.models.request_models import JobSettingsResponse, RunnerRegisterRequest


class LocalUserInternal(UserBase):
    password_hash: str
    is_admin: bool
    is_verified: bool
    provision_number: int | None


class OidcUserInternal(UserBase):
    iss: str
    sub: str


class LdapUserInternal(UserBase):
    provider_name: str
    uid: str


class RunnerInternal(BaseModel):
    id: int
    token_hash: str


class JobInternal(JobResponse):
    aborting: bool
    user_id: int
    job_settings_id: int | None = None
    audio_oid: int | None = None
    nonce: str | None = None


class JobSettingsResponseWrapped(BaseModel):
    settings: JobSettingsResponse


class JobAndSettingsInternal(JobAndSettingsResponse, JobInternal):
    pass


class InProcessJobInternal(InProcessJobResponse):
    progress: float = 0.0
    abort: bool = False


class TokenInfoInternal(TokenInfoResponse):
    user_id: int
    oidc_refresh_token_id: int | None = None


class LdapTokenInfoInternal(TokenInfoInternal):
    provider_name: str
    uid: str


class OidcTokenInfoInternal(TokenInfoInternal):
    iss: str
    sub: str


class LoginContext(BaseModel):
    user: UserResponse
    token: TokenInfoInternal


class AccountActivationTokenData(BaseModel):
    old_email: EmailValidated
    new_email: EmailValidated | None = None


class PasswordResetTokenData(BaseModel):
    email: EmailValidated


class LdapUserInfo(BaseModel):
    dn: str
    uid: str
    is_admin: bool
    email: EmailValidated


class JobSortKey(str, Enum):
    CREATION_TIME = "creation_time"
    FILENAME = "filename"


class InProcessJob(InProcessJobResponse):
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


class SSEEvent(str, Enum):
    JOB_UPDATED = "job_updated"
    JOB_CREATED = "job_created"
    JOB_DELETED = "job_deleted"
