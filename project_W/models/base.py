import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Self

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, HttpUrl, RootModel, SecretStr, model_validator


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


class JobBase(BaseModel):
    id: int
    creation_timestamp: datetime
    file_name: str
    finish_timestamp: datetime | None
    runner_name: str | None = Field(max_length=40)
    runner_id: int | None
    runner_version: str | None
    runner_git_hash: str | None = Field(max_length=40)
    runner_source_code_url: str | None
    downloaded: bool | None
    error_msg: str | None


class InProcessJobBase(BaseModel):
    id: int
    progress: float = Field(ge=0.0, le=100.0, default=0.0)
    abort: bool = False


class LocalAccountOperationModeEnum(str, Enum):
    DISABLED = "disabled"
    NO_SIGNUP_HIDDEN = "no-signup_hidden"
    NO_SIGNUP = "no-signup"
    ENABLED = "enabled"


class LocalAccountSettingsBase(BaseModel):
    mode: LocalAccountOperationModeEnum = Field(
        default=LocalAccountOperationModeEnum.ENABLED,
        description="""
        To what extend local accounts should be enabled.
        - enabled: Both login and signup possible and advertised in frontend to users (default).
        - no_signup: Login possible and advertised to users, signup not. Thus users can only login using already existing accounts (created through provisioning or by signup before this setting was set). Use this for example if you want users to login using local accounts that you created for them through provisioning.
        - no_signup_hidden: Login still possible but not advertised to users in the frontend. Especially helpful if the only local accounts should be provisioned admin accounts for administration purposes while normal users should only login using oidc or ldap accounts.
        - disabled: no login, no signup, no provisioned accounts. Login only through ldap and oidc. Please note that in this case you need to provide admin accounts through ldap or oidc as well!
        """,
        validate_default=True,
    )
    allowed_email_domains: list[
        Annotated[
            str,
            Field(
                pattern=r"^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+$",
                examples=["uni-heidelberg.de", "stud.uni-heidelberg.de"],
                description="Allowed domains in email addresses. Users will only be able to sign up/change their email of their local accounts if their email address uses one of these domains (the part after the '@'). If left empty, then all email domains are allowed.",
            ),
        ]
    ] = []
    allow_creation_of_api_tokens: bool = Field(
        default=True,
        description="If set to true then users logged in with local accounts can create api tokens with infinite lifetime. They will get invalidated if the user gets deleted.",
    )


class ProviderSettingsBase(BaseModel):
    hidden: bool = Field(
        default=False,
        description="Whether this provider should not be advertised to the user on the frontend. Useful if this provider should only provide admin accounts.",
        validate_default=True,
    )
    icon_url: HttpUrl | None = Field(
        default=None,
        description="URL to a square icon that will be shown to the user in the frontend next to the 'Login with <name>' to visually represent the account/identity provider. Should be a link to a square png with transparent background, or alternatively to a svg",
        examples=[
            "https://ssl.gstatic.com/images/branding/googleg/2x/googleg_standard_color_64dp.png"
        ],
    )
    allow_creation_of_api_tokens: bool = Field(
        default=False,
        description="If set to true then users logged in from this identity provider can create api tokens with infinite lifetime. These tokens will not be automatically invalidated if the user gets deleted or looses permissions in the identity provider. This means that with this setting enabled, users that ones have access to Project-W can retain that access possibly forever. Consider if this is a problem for you before enabling this!",
    )
