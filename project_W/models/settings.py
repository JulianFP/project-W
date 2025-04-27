from enum import Enum
from typing import Annotated

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    HttpUrl,
    UrlConstraints,
)


class ProvisionedUser(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(
        description="Email address of this user. This address will be treated as a verified email address, so make sure that it is valid",
        examples=[
            "admin@example.org",
            "user@example.org",
        ],
    )
    password: str = Field(
        description="The password of this user (for login). Please make sure that this password is secure, especially when provisioning admin users!"
    )
    is_admin: bool = Field(
        default=False,
        description="Whether this user should be an admin user. Be very careful with this, admin users have full access over all other users and their data! Warning: Revoking a users admin privileges over provisioning settings will currently not revoke any existing access tokens of that user, don't rely on that!",
        validate_default=True,
    )


class LocalAccountOperationModeEnum(str, Enum):
    disabled = "disabled"
    no_signup_hidden = "no-signup_hidden"
    no_signup = "no-signup"
    enabled = "enabled"


class LocalAccountSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: LocalAccountOperationModeEnum = Field(
        default=LocalAccountOperationModeEnum.enabled,
        description="""
        To what extend local accounts should be enabled.
        - enabled: Both login and signup possible and advertised in frontend to users (default).
        - no_signup: Login possible and advertised to users, signup not. Thus users can only login using already existing accounts (created through provisioning or by signup before this setting was set). Use this for example if you want users to login using local accounts that you created for them through provisioning.
        - no_signup_hidden: Login still possible but not advertised to users in the frontend. Especially helpful if the only local accounts should be provisioned admin accounts for administration purposes while normal users should only login using oidc or ldap accounts.
        - disabled: no login, no signup, no provisioned accounts. Login only through ldap and oidc. Please note that in this case you need to provide admin accounts through ldap or oidc as well!
        """,
        validate_default=True,
    )
    allow_creation_of_api_tokens: bool = Field(
        default=True,
        description="If set to true then users logged in with local accounts can create api tokens with infinite lifetime. They will get invalidated if the user gets deleted.",
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
    user_provisioning: Annotated[
        dict[int, ProvisionedUser],
        Field(
            description="Attribute set of users that should be created beforehand. Give every provisioned user a number using the key of this attribute set. This way the users email, password and admin privileges can still be changed later on using this config file. Warning: Deleting a user from this dict will not delete it from the application or database, use the /user/delete route for this!",
            examples=["0: {<ProvisionedUserSettings>}", "1: {<ProvisionedUserSettings>}"],
        ),
    ] = {}


class LocalTokenSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_secret_key: str = Field(
        # enforce 256-Bit secret keys (32 Byte = 64 characters in hex, half of it is supplied here, the other half comes from per user token secrets stored in database)
        min_length=32,
        max_length=32,
        pattern=r"^[a-f0-9]*$",  # hex
        description="The secret key used to generate JWT Tokens. Make sure to keep this secret since with this key an attacker could log in as any user. A new key can be generated with the following command: `python -c 'import secrets; print(secrets.token_hex(32))'`.",
    )
    session_expiration_time_minutes: int = Field(
        ge=5,
        default=60,
        description="Time for which a users/clients JWT Tokens stay valid (in minutes). After this time the user will be logged out automatically and has to authenticate again using their username and password.",
        validate_default=True,
    )


class ProviderSettings(BaseModel):
    allow_creation_of_api_tokens: bool = Field(
        default=False,
        description="If set to true then users logged in from this identity provider can create api tokens with infinite lifetime. These tokens will not be automatically invalidated if the user gets deleted or looses permissions in the identity provider. This means that with this setting enabled, users that ones have access to Project-W can retain that access possibly forever. Consider if this is a problem for you before enabling this!",
    )
    icon_url: HttpUrl | None = Field(
        default=None,
        description="URL to a square icon that will be shown to the user in the frontend next to the 'Login with <name>' to visually represent the account/identity provider",
        examples=[
            "https://ssl.gstatic.com/images/branding/googleg/2x/googleg_standard_color_64dp.png"
        ],
    )
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
    simple = "SIMPLE"
    md5 = "DIGEST-MD5"
    ntlm = "NTLM"


class LdapAuthSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mechanism: LdapAuthMechanismEnum = Field(
        default=LdapAuthMechanismEnum.simple,
        description="Authentication mechanism that should be used. Can be one of 'SIMPLE', 'DIGEST-MD5' or 'NTLM'",
    )
    user: str = Field(description="Identification of binding user.")
    password: str = Field(description="Password of binding user.")


class LdapProviderSettings(ProviderSettings):
    model_config = ConfigDict(extra="forbid")
    server_address: AnyUrl = Field(
        UrlConstraints(
            allowed_schemes=[
                "ldap",
                "ldaps",
                "ldapi",
            ],
        ),
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
        description="This disables the validation of the provided config file. This means that the server will start and run even though it loaded possibly invalid data which may cause it to crash or not work proberly. Only set this to 'true' for development or testing purposes, never in production!",
        validate_default=True,
    )
