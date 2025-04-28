import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, SecretStr

from .base import EmailValidated


def is_password_valid(password: SecretStr) -> SecretStr:
    match = re.match(
        r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[^a-zA-Z0-9]).{12,}$", password.get_secret_value()
    )
    if match is None:
        raise ValueError("Password does not meet required criteria")
    return password


class SignupData(BaseModel):
    email: str
    password: Annotated[SecretStr, AfterValidator(is_password_valid)]


class SignupDataVerified(BaseModel):
    email: EmailValidated
    password: Annotated[SecretStr, AfterValidator(is_password_valid)]
