from enum import Enum

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


class InProcessJob(BaseModel):
    """
    Represents a job that is currently being processed by a runner.
    Instances of this are created as soon as the runner retrieves the
    audio file from the server, and live until the server fully retrieves
    the completed transcript or until the runner fails.
    """

    runner_id: int
    job_id: int
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    abort: bool = False


class OnlineRunner(BaseModel):
    """
    Represents one instance of a runner that's currently registered as online. Note
    that this is separate from the Runner class that represents a runner database entry.
    Since job assignments and such don't persist across server restarts, we don't need to
    store them to the DB anyways.
    """

    runner_id: int
    runner_priority: int
    assigned_job_id: int | None = None
    in_process_job: int | None = None
    last_heartbeat_timestamp: float
