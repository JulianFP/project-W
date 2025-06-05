from enum import Enum
from typing import Mapping

from pydantic import BaseModel, Field

from .base import (
    InProcessJobBase,
    JobBase,
    JobSettingsBase,
    LocalAccountSettingsBase,
    ProviderSettingsBase,
    UserInDb,
)
from .request_data import JobSettings
from .settings import ImprintSettings


class UserTypeEnum(str, Enum):
    LOCAL = "local"
    LDAP = "ldap"
    OIDC = "oidc"


# user model for the api
class User(UserInDb):
    provider_name: str
    user_type: UserTypeEnum
    is_admin: bool
    is_verified: bool


# error response, is also being used when HTTPException is raised
class ErrorResponse(BaseModel):
    detail: str

    class Config:
        json_schema_extra = {
            "example": {"detail": "error message"},
        }


class AboutResponse(BaseModel):
    description: str
    source_code: str
    version: str
    imprint: ImprintSettings | None


class TokenSecretInfo(BaseModel):
    id: int
    name: str | None = Field(max_length=64)
    temp_token_secret: bool


class RunnerCreatedInfo(BaseModel):
    id: int
    token: str


class HeartbeatResponse(BaseModel):
    abort: bool = False
    job_assigned: bool = False


class RunnerJobInfoResponse(BaseModel):
    id: int
    settings: JobSettingsBase


class JobStatus(str, Enum):
    """
    Represents all the possible statuses that a
    job request might have.
    """

    # The job request has been received by the server,
    # but is not currently queued for processing.
    # TODO: Do we even need to support this?
    NOT_QUEUED = "not_queued"
    # The backend has received the job request but no
    # runner has been assigned yet
    PENDING_RUNNER = "pending_runner"
    # A runner has been assigned, but has not started processing
    # the request
    RUNNER_ASSIGNED = "runner_assigned"
    # A runner has been assigned, and is currently processing
    # the request
    RUNNER_IN_PROGRESS = "runner_in_progress"
    # The runner successfully completed the job and
    # the transcript is ready for retrieval
    SUCCESS = "success"
    # There was an error during the processing of the request
    FAILED = "failed"
    # The job was successfully completed, and the transcript
    # has been downloaded by the user.
    DOWNLOADED = "downloaded"


class JobAndSettings(JobBase):
    settings: JobSettings = JobSettings()


class JobInfo(JobAndSettings, InProcessJobBase):
    step: JobStatus


class AuthSettings(BaseModel):
    local_account: LocalAccountSettingsBase
    oidc_providers: Mapping[str, ProviderSettingsBase]
    ldap_providers: Mapping[str, ProviderSettingsBase]
