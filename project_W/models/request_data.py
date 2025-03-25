from fastapi.security import OAuth2PasswordRequestForm


# to be able to specify ldap_server on login
class AuthRequestForm(OAuth2PasswordRequestForm):
    ldap_server: str | None = None
