import re
from typing import Any, Self

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, RootModel, SecretStr, model_validator


class EmailValidated(RootModel):
    root: str

    @model_validator(mode="before")
    @classmethod
    def email_validation(cls, data: Any) -> Any:
        if isinstance(data, str):
            try:
                val_email = validate_email(data, check_deliverability=False)
                cls.__original = val_email.original
                cls.__domain = val_email.domain
                cls.__local_part = val_email.local_part
                return val_email.normalized
            except EmailNotValidError as e:
                raise ValueError(e)

    def get_domain(self) -> str:
        return self.__domain

    def get_original(self) -> str:
        return self.__original

    def get_local_part(self) -> str:
        return self.__local_part


class PasswordValidated(RootModel):
    root: SecretStr

    @model_validator(mode="after")
    def password_validation(self) -> Self:
        match = re.match(
            r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^a-zA-Z0-9]).{12,}$",
            self.root.get_secret_value(),
        )
        if match is None:
            raise ValueError(
                "The password needs to have at least one lowercase letter, uppercase letter, number, special character and at least 12 characters in total"
            )
        return self


class UserInDb(BaseModel):
    id: int
    email: EmailValidated
