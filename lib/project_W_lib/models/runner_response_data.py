from pydantic import BaseModel

from .job_settings import JobSettingsBase


class RegisteredResponse(BaseModel):
    id: int
    session_token: str


class HeartbeatResponse(BaseModel):
    abort: bool = False
    job_assigned: bool = False


class RunnerJobInfoResponse(BaseModel):
    id: int
    settings: JobSettingsBase
