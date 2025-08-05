from datetime import datetime
from enum import Enum
from typing import Mapping

from pydantic import BaseModel

from .base import (
    AdditionalUserInfo,
    InProcessJobBase,
    JobBase,
    JobSettingsBase,
    LocalAccountSettingsBase,
    ProviderSettingsBase,
    UserInDb,
)
from .request_data import JobSettings, SiteBanner
from .settings import ImprintSettings, TosSettings


class UserTypeEnum(str, Enum):
    LOCAL = "local"
    LDAP = "ldap"
    OIDC = "oidc"


# user model for the api
class User(UserInDb, AdditionalUserInfo):
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


class SiteBannerResponse(SiteBanner):
    id: int


class AboutResponse(BaseModel):
    description: str
    source_code: str
    version: str
    git_hash: str
    imprint: ImprintSettings | None
    terms_of_services: dict[int, TosSettings]
    job_retention_in_days: int | None
    site_banners: list[SiteBannerResponse]


class TokenInfo(BaseModel):
    id: int
    name: str
    admin_privileges: bool
    explicit: bool
    expires_at: datetime | None = None


class RunnerCreatedInfo(BaseModel):
    id: int
    token: str


class RegisteredResponse(BaseModel):
    id: int
    session_token: str


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
    # The job is currently being aborted, i.e. the backend waits
    # for the runner to stop processing this job
    ABORTING = "aborting"
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
