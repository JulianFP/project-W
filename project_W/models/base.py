from typing import Any

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, model_serializer, model_validator


class EmailValidated(BaseModel):
    original: str
    domain: str
    local_part: str
    normalized: str

    @model_validator(mode="before")
    @classmethod
    def email_validation(cls, data: Any) -> Any:
        if isinstance(data, str):
            try:
                return validate_email(data, check_deliverability=False).as_dict()
            except EmailNotValidError:
                raise ValueError("Invalid email format")
        return data

    @model_serializer
    def ser_model(self) -> str:
        return self.normalized


class UserInDb(BaseModel):
    id: int
    email: EmailValidated
