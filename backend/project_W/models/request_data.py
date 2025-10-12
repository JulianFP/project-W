from enum import Enum

from pydantic import BaseModel, SecretStr
from project_W_lib.models.job_settings import JobSettingsBase

from .base import EmailValidated, PasswordValidated


class SignupData(BaseModel):
    email: EmailValidated
    password: PasswordValidated


class PasswordResetData(BaseModel):
    token: SecretStr
    new_password: PasswordValidated


class JobSettings(JobSettingsBase):
    email_notification: bool = False


class TranscriptTypeEnum(str, Enum):
    TXT = "as_txt"
    SRT = "as_srt"
    TSV = "as_tsv"
    VTT = "as_vtt"
    JSON = "as_json"


class SiteBanner(BaseModel):
    html: str
    urgency: int


class EmailToUsers(BaseModel):
    subject: str
    body: str
