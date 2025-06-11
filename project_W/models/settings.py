from enum import Enum
from ipaddress import IPv4Interface
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    HttpUrl,
    IPvAnyInterface,
    PostgresDsn,
    RedisDsn,
    RootModel,
    SecretStr,
    SocketPath,
    UrlConstraints,
    model_validator,
)
from pydantic_core import Url

from .base import (
    EmailValidated,
    LocalAccountSettingsBase,
    PasswordValidated,
    ProviderSettingsBase,
)


class ProvisionedUser(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailValidated = Field(
        description="Email address of this user. This address will be treated as a verified email address, so make sure that it is valid",
        examples=[
            "admin@example.org",
            "user@example.org",
        ],
    )
    password: PasswordValidated = Field(
        description="The password of this user (for login). Please make sure that this password is secure, especially when provisioning admin users!"
    )
    is_admin: bool = Field(
        default=False,
        description="Whether this user should be an admin user. Be very careful with this, admin users have full access over all other users and their data! Warning: Revoking a users admin privileges over provisioning settings will currently not revoke any existing access tokens of that user, don't rely on that!",
        validate_default=True,
    )


class LocalAccountSettings(LocalAccountSettingsBase):
    model_config = ConfigDict(extra="forbid")
    user_provisioning: Annotated[
        dict[int, ProvisionedUser],
        Field(
            description="Attribute set of users that should be created beforehand. Give every provisioned user a number using the key of this attribute set. This way the users email, password and admin privileges can still be changed later on using this config file. Warning: Deleting a user from this dict will not delete it from the application or database, use the /user/delete route for this!",
            examples=["0: {<ProvisionedUserSettings>}", "1: {<ProvisionedUserSettings>}"],
        ),
    ] = {}


class SessionTokenValidated(RootModel):
    root: SecretStr

    @model_validator(mode="after")
    def password_validation(self) -> Self:
        # enforce 256-Bit secret keys (32 Byte = 64 characters in hex, if second half is supplied by database then only first half of that is used)
        if len(self.root.get_secret_value()) != 64:
            raise ValueError(
                "The session token has to be exactly 64 characters in length. Use the command `python -c 'import secrets; print(secrets.token_hex(32))'` to generate a valid session token!"
            )
        return self


class LocalTokenSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_secret_key: SessionTokenValidated = Field(
        description="The secret key used to generate JWT Tokens. Make sure to keep this secret since with this key an attacker could log in as any user. A new key can be generated with the following command: `python -c 'import secrets; print(secrets.token_hex(32))'`.",
    )
    session_expiration_time_minutes: int = Field(
        ge=5,
        default=60,
        description="Time for which a users/clients JWT Tokens stay valid (in minutes). After this time the user will be logged out automatically and has to authenticate again using their username and password.",
        validate_default=True,
    )


class ProviderSettings(ProviderSettingsBase):
    ca_pem_file_path: FilePath | None = Field(
        default=None,
        description="Path to the pem certs file that includes the certificates that should be trusted for this provider (alternative certificate verification). Useful if the identity provider uses a self-signed certificate",
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


class OidcProviderSettings(ProviderSettings):
    model_config = ConfigDict(extra="forbid")
    base_url: HttpUrl = Field(
        description="Base url of the OIDC provider. If '/.well-known/openid-configuration' is appended to it it should return its metadata",
        examples=[
            "https://accounts.google.com",
            "https://appleid.apple.com",
        ],
    )
    client_id: str = Field(
        description="The client_id string as returned by the identity provider after setting up this application"
    )
    client_secret: SecretStr = Field(
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


class LdapQuerySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_dn: str = Field(
        description="The base DN under which should be searched",
        examples=["dc=example,dc=org"],
    )
    filter: str = Field(
        description="Ldap filter expression that should return only one user with a specific username that has the required permissions. Use %s as a placeholder for the username as the user enters it into on the login form.",
        examples=[
            "(&(class=person)(person=%s))"
            "(&(class=person)(memberof=spn=project-W-users@localhost)(name=%s))"
            "(&(class=person)(memberof=spn=project-W-admins@localhost)(mail=%s))"
        ],
    )
    mail_attribute_name: str = Field(
        description="The attribute/field name that contains the email address of a user. Every user that should be able to authenticate with Project-W should have this attribute.",
        examples=[
            "mail",
            "email",
            "mail1",
        ],
    )


class LdapAuthMechanismEnum(str, Enum):
    SIMPLE = "SIMPLE"
    MD5 = "DIGEST-MD5"
    NTLM = "NTLM"


class LdapAuthSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mechanism: LdapAuthMechanismEnum = Field(
        default=LdapAuthMechanismEnum.SIMPLE,
        description="Authentication mechanism that should be used. Can be one of 'SIMPLE', 'DIGEST-MD5' or 'NTLM'",
    )
    user: str = Field(description="Identification of binding user.")
    password: SecretStr = Field(description="Password of binding user.")


class LdapProviderSettings(ProviderSettings):
    model_config = ConfigDict(extra="forbid")
    server_address: Annotated[
        Url,
        UrlConstraints(
            allowed_schemes=[
                "ldap",
                "ldaps",
                "ldapi",
            ],
        ),
    ] = Field(
        description="Address of the ldap server. Should start with either ldap://, ldaps:// or ldapi:// depending on whether the connection should be unencrypted, ssl/tls encrypted or if it's an URL-encoded filesocket connection",
        examples=[
            "ldap://example.org",
            "ldaps://example.org",
            "ldapi://%2Frun%2Fslapd%2Fldapi",
        ],
    )
    user_query: LdapQuerySettings | None = Field(
        default=None,
        description="Settings that define how normal users should be queried from the ldap server. If left to None then no normal user will be able to sign in using this provider",
    )
    admin_query: LdapQuerySettings | None = Field(
        default=None,
        description="Settings that define how admin users should be queried from the ldap server. If left to None then no admin user will be able to sign in (with admin privileges) using this provider",
    )
    service_account_auth: LdapAuthSettings = Field(
        description=" This user should be a service account with read permissions on all other users and their mail (and any other attributes used in the query, e.g. memberof)."
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
    ldap_providers: Annotated[
        dict[str, LdapProviderSettings],
        Field(
            description="Attribute set of identity providers. The name of the set will be shown to users in a form like this: 'Login with <provider name>'.",
            examples=["Google: {<ProviderSettings>}", "Apple: {<ProviderSettings>}"],
        ),
    ] = {}


class SMTPSecureEnum(str, Enum):
    SSL = "ssl"
    STARTTLS = "starttls"
    PLAIN = "plain"


class SMTPServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hostname: str = Field(
        pattern=r"^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost$",
        description="FQDN of your smtp server.",
    )
    port: int = Field(
        ge=0,
        le=65535,
        default=587,
        description="Port that should be used for the smtp connection.",
    )
    secure: SMTPSecureEnum = Field(
        default=SMTPSecureEnum.STARTTLS,
        description="Whether to use 'ssl', 'starttls' or no encryption ('plain') with the smtp server.",
    )
    sender_email: EmailValidated = Field(
        description="Email address from which emails will be sent to the users.",
    )
    username: str | None = Field(
        default=None,
        description="Username that should be used to authenticate with the smtp server. Most of the time this is the same as 'senderEmail'.",
        validate_default=True,
    )
    password: SecretStr | None = Field(
        default=None,
        description="Password that should be used to authenticate with the smtp server.",
        validate_default=True,
    )


class RedisConnection(BaseModel):
    connection_string: RedisDsn | None = Field(
        default=None,
        description="Redis connection string to connect to the caching database that should be used by Project-W.",
        validate_default=True,
    )
    unix_socket_path: SocketPath | None = Field(
        default=None,
        description="Path to a redis unix socket. Can be used instead of connection_string",
        validate_default=True,
    )

    @model_validator(mode="after")
    def either_connection_string_unix_socket_path(self) -> Self:
        if self.connection_string is None and self.unix_socket_path is None:
            raise ValueError(
                "You need to set either connection_string or unix_socket_path for your Redis connection"
            )
        if self.connection_string is not None and self.unix_socket_path is not None:
            raise ValueError("You can only define one of connection_string or unix_socket_path")
        return self


class ImprintSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="The name of the person/institution hosting this instance",
    )
    email: EmailValidated = Field(
        description="The contact email address of the person/institution hosting this instance",
    )
    additional_imprint_html: str | None = Field(
        description="Content of the imprint in addition to the other fields",
        default=None,
        validate_default=True,
    )


class SslSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cert_file: FilePath = Field(
        description="Path to the SSL certificate file",
    )
    key_file: FilePath = Field(
        description="Path to the SSL key file",
    )
    key_file_password: SecretStr | None = Field(
        description="Password of the SSL key file",
        default=None,
        validate_default=True,
    )


class WebServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ssl: SslSettings | None = Field(
        description="SSL settings to enable https encrypted traffic",
        default=None,
        validate_default=True,
    )
    no_https: bool = Field(
        description="Disable https encryption. This will lead to passwords, sensitive data and more to be transmitted unencrypted! Only set this for development or testing purposes!",
        default=False,
        validate_default=True,
    )
    worker_count: int = Field(
        description="Amount of workers that should serve the web server simultaneously. Increasing this will allow for more concurrent users as long as it is lower or equal than the amount of CPU cores on your system.",
        default=4,
    )
    address: IPvAnyInterface = Field(
        description="The address of the interface under which the web server should be served.",
        default=IPv4Interface("127.0.0.1"),
    )
    port: int = Field(
        ge=0,
        le=65535,
        default=8000,
        description="The port under which the web server should be served",
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
    web_server: WebServerSettings = Field(
        description="Settings regarding the web server deployment of this application",
        default=WebServerSettings(),
        validate_default=True,
    )
    postgres_connection_string: PostgresDsn = Field(
        description="PostgreSQL connection string to connect to the database that should be used by Project-W. See https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING for the syntax.",
        validate_default=True,
    )
    redis_connection: RedisConnection
    security: SecuritySettings
    smtp_server: SMTPServerSettings
    imprint: ImprintSettings | None = Field(
        description="Set the imprint/impressum of this instance",
        default=None,
        validate_default=None,
    )
