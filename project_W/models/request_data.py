from pydantic import BaseModel, SecretStr

from .base import EmailValidated, PasswordValidated


class SignupData(BaseModel):
    email: EmailValidated
    password: PasswordValidated


class PasswordResetData(BaseModel):
    token: SecretStr
    new_password: PasswordValidated
