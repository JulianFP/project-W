from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class LocalAccountSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disable: bool = Field(
        default=False,
        description="Whether users should be able to authenticate using local accounts (stored in local PostgreSQL database). Only disable if you want to enforce authentication over LDAP or OIDC providers.",
        validate_default=True,
    )
    disable_signup: bool = Field(
        default=False,
        description="Whether signup of new local accounts should be possible. If set to 'true' then only users who already have an local account will be able to login with it. Mostly useful if only the admin account should be local but everybody else should authenticate using LDAP or OIDC instead.",
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


class LocalTokenSettings(BaseModel):
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


class OidcRoleSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="Name of the required role/group",
        examples=[
            "project-W-users",
            "project-W-admins",
            "admins",
            "employees",
        ],
    )
    field_name: str = Field(
        description="Name of the field/claim under which the role list is available in the id token",
        examples=[
            "roles",
            "groups",
        ],
    )


class OidcProviderSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    icon_url: str | None = Field(
        default=None,
        description="URL to an square icon that will be shown to the user in the frontend next to the 'Login with <name>' to visually represent the account/identity provider",
        examples=[
            "https://ssl.gstatic.com/images/branding/googleg/2x/googleg_standard_color_64dp.png"
        ],
    )
    base_url: str = Field(
        pattern=r"^(http|https):\/\/(([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost)(:[0-9]+)?((\/[a-zA-Z0-9\-]+)+)?$",
        description="Base url of the OIDC provider. If '/.well-known/openid-configuration' is appended to it it should return its metadata",
        examples=[
            "https://accounts.google.com",
            "https://appleid.apple.com",
        ],
    )
    client_id: str = Field(
        description="The client_id string as returned by the identity provider after setting up this application"
    )
    client_secret: str = Field(
        description="The client_secret string as returned by the identity provider after setting up this application"
    )
    user_role: OidcRoleSettings | None = Field(
        default=None,
        description="Configure the role that users should have to be able to access this Project-W instance. Every user who doesn't have this role in their id token won't be able to use this service. Set to None if all users of this IdP should be able to access it",
    )
    admin_role: OidcRoleSettings | None = Field(
        default=None,
        description="Configure the role that users should have to be have admin permissions on Project-W. Only users with this role can do things like create new runners and see all user data. Use carefully! Set to None if no users of this IdP should be admins",
    )
    ca_pem_file_path: str = Field(
        default=None,
        description="Path to the pem certs file that includes the certificates that should be trusted for this provider (alternative certificate verification). Useful if the identity provider uses a self-signed certificate",
    )


# modeling the config file (descriptions and examples are used for documentation)
class SecuritySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    local_account: LocalAccountSettings = LocalAccountSettings()
    local_token: LocalTokenSettings
    oidc_providers: Annotated[
        dict[str, OidcProviderSettings],
        Field(
            description="Attribute set of identity providers. The name of the set will be shown to users in a form like this: 'Login with <provider name>'.",
            examples=["Google: {<ProviderSettings>}", "Apple: {<ProviderSettings>}"],
        ),
    ] = {}


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
    security: SecuritySettings
    smtp_server: SMTPServerSettings
    disable_option_validation: bool = Field(
        default=False,
        description="This disables the jsonschema validation of the provided config file. This means that the server will start and run even though it loaded possibly invalid data which may cause it to crash or not work proberly. Only set this to 'true' for development or testing purposes, never in production!",
        validate_default=True,
    )
