from pydantic import BaseModel

from .internal import UserInDb


# user model for the api
class User(UserInDb):
    provider_name: str
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
