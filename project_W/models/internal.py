from pydantic import BaseModel


# user models for the database
class UserInDb(BaseModel):
    id: int
    email: str


class LocalUserInDb(UserInDb):
    password_hash: str
    is_admin: bool
    is_verified: bool


class OidcUserInDb(UserInDb):
    iss: str
    sub: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: str
    email: str
    is_verified: bool


class DecodedTokenData(TokenData):
    is_admin: bool
    iss: str
    sub: str


# we only include the fields relevant for our application here. There are many more: https://openid.net/specs/openid-connect-discovery-1_0.html
class OpenIdConfiguration(BaseModel):
    jwks_uri: str
    id_token_signing_alg_values_supported: list[str]


class OidcPublicKey(BaseModel):
    e: str
    n: str
    kty: str
    kid: str
    use: str
    alg: str


class OidcAuthServerInfo(BaseModel):
    jwks_uri: str
    id_token_signing_alg_values_supported: list[str]
    scopes_supported: list[str]
    claims_supported: list[str]


class JwksUriResponse(BaseModel):
    keys: list[OidcPublicKey]
