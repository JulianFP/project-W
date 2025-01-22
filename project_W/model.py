from typing import Annotated

from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field


# modeling the config file (descriptions and examples are used for documentation)
class LoginSecuritySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_secret_key: str = Field(
        min_length=64,  # enforce at least 256-Bit secret keys (32 Byte = 64 characters in hex)
        pattern=r"^[a-f0-9]*$",  # hex
        description="The secret key used to generate JWT Tokens. Make sure to keep this secret since with this key an attacker could log in as any user. A new key can be generated with the following command: `python -c 'import secrets; print(secrets.token_hex(32))'`.",
    )
    session_expiration_time_minutes: int = Field(
        ge=5,
        default=60,
        description="Time for which a users/clients JWT Tokens stay valid (in minutes). After this time the user will be logged out automatically and has to authenticate again using their username and password.",
        validate_default=True,
    )
    allowed_email_domains: list[
        Annotated[
            str,
            Field(
                pattern=r"^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+$",
                examples=["uni-heidelberg.de", "stud.uni-heidelberg.de"],
                description="Allowed domains in email addresses. Users will only be able to sign up/change their email if their email address uses one of these domains (the part after the '@'). If left empty, then all email domains are allowed.",
            ),
        ]
    ] = []
    disable_signup: bool = Field(
        default=False,
        description="Whether signup of new accounts should be possible. If set to 'true' then only users who already have an account will be able to use the service.",
        validate_default=True,
    )


class SMTPServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str = Field(
        pattern=r"^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost$",
        description="FQDN of your smtp server.",
    )
    port: int = Field(
        ge=0,
        le=65535,
        description="Port that should be used for the smtp connection.",
    )
    secure: str = Field(
        pattern=r"^ssl|starttls|unencrypted$",
        description="Whether to use ssl, starttls or no encryption with the smtp server.",
    )
    sender_email: str = Field(
        description="Email address from which emails will be sent to the users.",
    )
    username: str | None = Field(
        default=None,
        description="Username that should be used to authenticate with the smtp server. Most of the time this is the same as 'senderEmail'.",
        validate_default=True,
    )
    password: str | None = Field(
        default=None,
        description="Password that should be used to authenticate with the smtp server.",
        validate_default=True,
    )


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_url: str = Field(
        pattern=r"^(http|https):\/\/(([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost)(:[0-9]+)?((\/[a-zA-Z0-9\-]+)+)?(\/#)?$",
        description="URL under which the frontend is served. It is used for providing the user with clickable links inside of account-activation or password-reset emails. The URL should fullfill the following requirements:\n\n- It has to start with either 'http://' or 'https://'\n\n- It should contain the port number if it is not just 80 (default of http) or 443 (default of https)\n\n- It should contain the root path under which the frontend is served if its not just /\n- It should end with /# if the frontend uses hash based routing (which our frontend does!)",
        examples=[
            "https://example.com/#",
            "https://sub.example.org/apps/project-W/frontend/#",
            "http://localhost:5173/#",
            "http://192.168.1.100:5173/#",
        ],
    )
    postgres_connection_string: str = Field(
        default="host=/var/run/postgresql dbname=postgres user=postgres",
        description="PostgreSQL connection string to connect to the database that should be used by Project-W. See https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING for the syntax.",
        validate_default=True,
    )
    login_security: LoginSecuritySettings
    smtp_server: SMTPServerSettings
    disable_option_validation: bool = Field(
        default=False,
        description="This disables the jsonschema validation of the provided config file. This means that the server will start and run even though it loaded possibly invalid data which may cause it to crash or not work proberly. Only set this to 'true' for development or testing purposes, never in production!",
        validate_default=True,
    )


# user model for the api
class User(BaseModel):
    id: int
    email: str
    is_admin: bool
    activated: bool


# user model for the database
class UserInDb(User):
    password_hash: str


# to be able to specify ldap_server on login
class AuthRequestForm(OAuth2PasswordRequestForm):
    ldap_server: str | None = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str
    scopes: list[str] = []


# every error response should have a detail attached
class ErrorResponse(BaseModel):
    detail: str


class AboutResponse(BaseModel):
    description: str
    source_code: str
    version: str
