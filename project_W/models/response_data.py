from pydantic import BaseModel

from .internal import UserInDb


# user model for the api
class User(UserInDb):
    provider_name: str
    is_admin: bool
    is_verified: bool


# every error response should have a detail attached
class ErrorResponse(BaseModel):
    detail: str


class AboutResponse(BaseModel):
    description: str
    source_code: str
    version: str
