from pydantic import BaseModel

from .base import JobSettingsBase


# error response, is also being used when HTTPException is raised
class ErrorResponse(BaseModel):
    detail: str

    class Config:
        json_schema_extra = {
            "example": {"detail": "error message"},
        }


class RegisteredResponse(BaseModel):
    id: int
    session_token: str


class HeartbeatResponse(BaseModel):
    abort: bool = False
    job_assigned: bool = False


class RunnerJobInfoResponse(BaseModel):
    id: int
    settings: JobSettingsBase
