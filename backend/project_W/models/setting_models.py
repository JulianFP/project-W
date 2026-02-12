from enum import Enum
from ipaddress import IPv4Interface
from typing import Annotated, Mapping, Self

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

from project_W_lib.models.base import EmailValidated
from project_W_lib.models.response_models import (
    ImprintResponse,
    TosResponse,
    LocalAccountOperationModeEnum,
    LocalAccountResponse,
    ProviderResponse,
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
    password: SecretStr = Field(
        min_length=12,
        description="The password of this user (for login). Please make sure that this password is secure, especially when provisioning admin users!",
    )
    is_admin: bool = Field(
        default=False,
        description="Whether this user should be an admin user. Be very careful with this, admin users have full access over all other users and their data! Warning: Revoking a users admin privileges over provisioning settings will currently not revoke any existing access tokens of that user, don't rely on that!",
        validate_default=True,
    )


class LocalAccountSettings(LocalAccountResponse):
    model_config = ConfigDict(extra="forbid")
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
                description="Allowed domains in email addresses. Users will only be able to sign up/change their email of their local accounts if their email address uses one of these domains (the part after the '@'). If left empty, then all email domains are allowed.",
            ),
        ]
    ] = []
    allow_creation_of_api_tokens: bool = Field(
        default=True,
        description="If set to true then users logged in with local accounts can create api tokens with infinite lifetime. They will get invalidated if the user gets deleted.",
        validate_default=True,
    )
    user_provisioning: Annotated[
        dict[int, ProvisionedUser],
        Field(
            description="Attribute set of users that should be created beforehand. Give every provisioned user a number using the key of this attribute set. This way the users email, password and admin privileges can still be changed later on using this config file. Warning: Deleting a user from this dict will not delete it from the application or database, use the /user/delete route for this!",
            examples=["0: {<ProvisionedUserSettings>}", "1: {<ProvisionedUserSettings>}"],
        ),
    ] = {}


class SecretKeyValidated(RootModel):
    root: SecretStr

    @model_validator(mode="after")
    def session_token_validation(self) -> Self:
        # enforce 256-Bit secret keys (32 Byte = 64 characters in hex, if second half is supplied by database then only first half of that is used)
        as_bytes = bytes.fromhex(self.root.get_secret_value())
        if len(as_bytes) != 32:
            raise ValueError(
                "The secret key has to be 256-bit encoded in hex (64 string characters). Use the command `python -c 'import secrets; print(secrets.token_hex(32))'` to generate a valid secret key!"
            )
        return self


class TokenSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_expiration_time_minutes: int = Field(
        ge=15,
        default=60,
        description="Time for which auth tokens stay valid (not API tokens, they stay valid indefinitely). Project-W uses rolling tokens, so beginning from 10 minutes before expiration the auth token will be rotated automatically to prevent active users from being logged out. Inactive users however will be logged out after this period. Increase if you want to keep inactive users logged in for longer (on the prize of a higher risk of the auth token being stolen)",
        validate_default=True,
    )
    rolling_session_before_expiration_minutes: int = Field(
        ge=5,
        default=10,
        description="The amount of minutes before a token expires when a user should get a new auth token if the user is still active",
        validate_default=True,
    )

    @model_validator(mode="after")
    def rlling_session_before_session_significantly_smaller_than_session_exp(self) -> Self:
        if (
            self.rolling_session_before_expiration_minutes
            > 0.4 * self.session_expiration_time_minutes
        ):
            raise ValueError(
                "'rolling_session_before_expiration_minutes' is too large compared to 'session_expiration_time_minutes'!"
            )
        return self


class ProviderSettings(ProviderResponse):
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
        validate_default=True,
    )
    allow_creation_of_api_tokens: bool = Field(
        default=True,
        description="If set to true then users logged in from this identity provider can create api tokens with infinite lifetime. These tokens will be automatically invalidated if the user gets deleted from the identity provider ones the periodic background job gets called. Run the periodic background task more often to get user access revoked quicker.",
        validate_default=True,
    )
    ca_pem_file_path: FilePath | None = Field(
        default=None,
        description="Path to the pem certs file that includes the certificates that should be trusted for this provider (alternative certificate verification). Useful if the identity provider uses a self-signed certificate",
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


class OidcClaimMap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(
        description="The name of the claim containing the email address",
        default="email",
        validate_default=True,
    )
    email_verified: str = Field(
        description="The name of the claim that is only present if the user's email was verified",
        default="email_verified",
        validate_default=True,
    )


class OidcClientAuthMethod(str, Enum):
    CLIENT_SECRET_POST = "client_secret_post"
    CLIENT_SECRET_BASIC = "client_secret_basic"


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
    client_auth_method: OidcClientAuthMethod = Field(
        default=OidcClientAuthMethod.CLIENT_SECRET_BASIC,
        validate_default=True,
        description="The authentication method of the authorization request. Can be set to 'client_secret_basic' (default, Authorization header), or 'client_secret_post' (in the body of a POST)",
    )
    additional_authorize_params: dict[str, str] = Field(
        default={},
        validate_default=True,
        description="Additional URI parameters to add to the authorization request (made to the authorization_endpoint in the OIDC discovery document). Useful if your IdP requires additional parameters to return all required data (e.g. Google requires additional parameters to reliably return refresh_tokens)",
    )
    scopes: list[str] = Field(
        default=["email"],
        validate_default=True,
        description="Scopes that should be requested from the IdP (in addition to the 'openid' scope). Use this if your OIDC provider doesn't comply with https://openid.net/specs/openid-connect-core-1_0.html#ScopeClaims and needs a different scope than 'email'.",
    )
    claim_map: OidcClaimMap = Field(
        default=OidcClaimMap(),
        validate_default=True,
        description="In addition to the 'sub' and 'iss' claims Project-W also needs to get a verified email address from the OIDC provider. By default it also needs the 'email' and 'email_verified' claims for this (as defined in https://openid.net/specs/openid-connect-core-1_0.html#ScopeClaims). With this settings you can change these values to something else if your OIDC provider returns the email address in a claim with a different name.",
    )
    enable_pkce_s256_challenge: bool = Field(
        default=True,
        description="Whether the PKCE flow using the S256 challenge method should be enabled. The OIDC provider has to support this.",
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
        description="Ldap filter expression that that will be merged with the user attribute filters.",
        examples=[
            "(class=person)"
            "(&(class=person)(memberof=spn=project-W-users@localhost)"
            "(&(class=account)(memberof=spn=project-W-admins@localhost))"
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
    username_attributes: list[str] = Field(
        description="A list of attribute/field names which contain strings that can be used by the user as a username during login. Project-W will use them to generate an LDAP filter expression and merge it with your provided filter expression like this: (&(<your filter expression>)(|(<username_attribute1>=<username>)(<username_attribute2>=<username>)...))",
        examples=[
            ["name"],
            ["name", "mail"],
            ["displayname", "email"],
        ],
    )
    uid_attribute: str = Field(
        description="The attribute/field name that contains a unique user identifier. Doesn't have to be the same as one of the username_attributes, but can be. Make sure that this identifier is unique to a user across the LDAP directory and will never change/be reassigned to a different user! Every LDAP user that the filter expression can return should have this attribute exactly ones. This attribute in combination with the filter expression will be used to query users outside of the regular login flow.",
        examples=[
            "uid",
            "uuid",
        ],
    )
    mail_attribute: str = Field(
        description="The attribute/field name that contains the email address of a user.  Every LDAP user that the filter expression can return should have this attribute exactly ones.",
        examples=[
            "mail",
            "email",
            "mail1",
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
    secret_key: SecretKeyValidated = Field(
        description="The secret key used to sign payloads in emails. Make sure to keep this secret since with this key an attacker could log in as any user. A new key can be generated with the following command: `python -c 'import secrets; print(secrets.token_hex(32))'`.",
    )
    local_account: LocalAccountSettings = LocalAccountSettings()
    tokens: TokenSettings = TokenSettings()
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
        pattern=r"^[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)*$",
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


class ImprintSettings(ImprintResponse):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="The name of the person/institution hosting this instance",
    )
    email: EmailValidated | None = Field(
        description="A contact email address of the person/institution hosting this instance",
        default=None,
        validate_default=True,
    )
    url: HttpUrl | None = Field(
        description="The URL to forward users to if they click on the imprint button on the frontend. Useful if you want to link to an imprint on a different website instead of having a dedicated imprint for Project-W. Mutually exclusive with the 'additional_imprint_html' option.",
        default=None,
        validate_default=True,
    )
    additional_imprint_html: str | None = Field(
        description="Content of the imprint in addition to the name and email fields. Mutually exclusive with the 'url' option.",
        default=None,
        validate_default=True,
    )


class TosSettings(TosResponse):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="The name of this term of service. This will be shown as a title above the tos_html content in the frontend",
    )
    version: int = Field(
        description="The version of this term of service. Start by putting this to 1. When incremented then users will have to re-accept these terms.",
    )
    tos_html: str = Field(
        description="The terms of services in html format. You may include links to external websites if you want.",
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


class ReverseProxySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trusted_proxies: list[str] = Field(
        description="List of IP addresses to trust as the proxy from which traffic originates",
    )
    root_path: str | None = Field(
        description="Set this option to your path prefix if you want to serve Project-W from a root path prefix at your proxy",
        default=None,
    )


class WebServerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed_hosts: list[str] = Field(
        description="List of domains that are allowed as hostnames. Wildcard domains supported",
        default=["*"],
        validate_default=True,
    )
    reverse_proxy: ReverseProxySettings | None = Field(
        description="Settings for when running Project-W behind a Reverse Proxy",
        default=None,
    )
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
        default=1,
    )
    address: IPvAnyInterface = Field(
        description="The address of the interface under which the web server should be served.",
        default=IPv4Interface("0.0.0.0"),
    )
    port: int = Field(
        ge=0,
        le=65535,
        default=5000,
        description="The port under which the web server should be served. The default port is 5000 regardless of whether https is enabled or not. This shouldn't be changed in a docker deployment because that would break the docker container's health check. Use docker's port mapping feature instead.",
    )


class CleanupSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finished_job_retention_in_days: int | None = Field(
        description="For how long to keep finished jobs. If a job is older than this it can be cleaned up by the database cleanup task (please note that you have to setup this task as a cronjob or use the cronjob docker container!). If set to None then job cleanup is disabled",
        default=None,
        ge=1,
    )
    user_retention_in_days: int | None = Field(
        description="For how long to keep users and their data. If a user hasn't logged in to Project-W in the specified time frame then the user may be deleted (please note that you have to setup this task as a cronjob or use the cronjob docker container!). If set to None then job cleanup is disabled",
        default=None,
        ge=90,
    )


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_url: str = Field(
        pattern=r"^(http|https):\/\/(([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost)(:[0-9]+)?((\/[a-zA-Z0-9\-]+)+)?(\/#)?$",
        description="URL under which the frontend is served. It is used for providing the user with clickable links inside of account-activation or password-reset emails. The URL should fulfill the following requirements:\n\n- It has to start with either 'http://' or 'https://'\n\n- It should contain the port number if it is not just 80 (default of http) or 443 (default of https)\n\n- It should contain the root path under which the frontend is served if its not just /\n- It should end with /# if the frontend uses hash based routing (which our frontend does!)",
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
        validate_default=True,
    )
    terms_of_services: Annotated[
        Mapping[int, TosSettings],
        Field(
            description="Attribute set of terms of services. The user will have to accept to every one of these separately before they can use the service. The name of the set will be id of the term of service, don't change it once set!",
        ),
    ] = {}
    cleanup: CleanupSettings = Field(
        description="Settings regarding cleanups of this server's database. This requires the cronjob to be set up correctly!",
        default=CleanupSettings(),
        validate_default=True,
    )
