from enum import Enum

from pydantic import BaseModel, Field

from .base import UserInDb


class UserTypeEnum(str, Enum):
    local = "local"
    ldap = "ldap"
    oidc = "oidc"


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


class TokenSecretInfo(BaseModel):
    id: int
    name: str | None = Field(max_length=64)
    temp_token_secret: bool


class RunnerCreatedInfo(BaseModel):
    id: int
    token: str
