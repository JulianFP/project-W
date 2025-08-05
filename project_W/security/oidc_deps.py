import ssl
from json.decoder import JSONDecodeError

import certifi
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from httpx import AsyncClient, HTTPError, HTTPStatusError
from pydantic import SecretStr

import project_W.dependencies as dp

from ..logger import get_logger
from ..models.base import EmailValidated
from ..models.internal import OidcTokenInfoInternal
from ..models.settings import OidcProviderSettings, OidcRoleSettings, Settings

oauth = OAuth()

oauth_iss_to_name = {}
oauth_iss_to_nice_name = {}
local_oidc_prov: dict[str, OidcProviderSettings] = (
    {}
)  # local copy of settings with normalized provider names
oauth_iss_to_config: dict[str, dict] = {}
oauth_iss_to_ctx: dict[str, ssl.SSLContext] = {}

logger = get_logger("project-W")


async def register_with_oidc_providers(config: Settings):
    oidc_prov = config.security.oidc_providers
    if oidc_prov is {}:
        raise Exception("Tried to use oidc router even though oidc is disabled in config!")
    for name, idp in oidc_prov.items():
        logger.info(f"Trying to connect with OIDC provider {name}...")
        # normalize provider name
        norm_name = name.lower().strip()
        local_oidc_prov[norm_name] = idp

        if idp.ca_pem_file_path:
            cafile = str(idp.ca_pem_file_path)
        else:
            cafile = certifi.where()
        ctx = ssl.create_default_context(cafile=cafile)

        base_url = str(idp.base_url)
        if base_url[-1] != "/":
            base_url += "/"
        async with AsyncClient(verify=ctx) as client:
            metadata_uri = f"{base_url}.well-known/openid-configuration"
            oauth.register(
                norm_name,
                client_id=idp.client_id,
                client_secret=idp.client_secret.get_secret_value(),
                server_metadata_url=metadata_uri,
                code_challenge_method="S256" if idp.enable_pkce_s256_challenge else None,
                client_kwargs={
                    "scope": "openid email",
                    "verify": ctx,
                },
            )

            try:
                oidc_config = (await client.get(metadata_uri)).raise_for_status().json()
            except (HTTPError, HTTPStatusError, JSONDecodeError) as e:
                raise Exception(
                    f"Error occured while trying to connect to the metadata uri of the oidc provider '{name}': {type(e).__name__}"
                )
            issuer = oidc_config["issuer"]
            oauth_iss_to_nice_name[issuer] = name
            oauth_iss_to_name[issuer] = norm_name
            oauth_iss_to_config[issuer] = oidc_config
            oauth_iss_to_ctx[issuer] = ctx
        logger.info(f"Connected with OIDC provider {name}")


def has_role(role_conf: OidcRoleSettings, user) -> bool:
    role_name = user.get(role_conf.field_name)
    if isinstance(role_name, list):
        return role_conf.name in role_name
    else:
        return role_name == role_conf.name


def get_provider_name(iss: str) -> str:
    provider_name = oauth_iss_to_nice_name.get(iss)
    if not provider_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication successful, but the user was not found in database",
        )
    return provider_name


def validate_oidc_attributes(provider_name: str, oidc_attrs: dict) -> bool:
    if not oidc_attrs.get("iss"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get iss from the identity provider. Please make sure that the IdP supports the iss claim",
        )
    if not oidc_attrs.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get sub from the identity provider. Please make sure that the IdP supports the sub claim",
        )
    if not EmailValidated.model_validate(oidc_attrs.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get a valid email address from the identity provider. Please make sure that the IdP supports the email claim, that your account has an email address associated with it and that this email is valid",
        )
    if not oidc_attrs.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The email address of this OIDC '{provider_name}' account is not verified",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )

    # check if user is admin
    admin_role_conf = local_oidc_prov[provider_name].admin_role
    if admin_role_conf is not None and has_role(admin_role_conf, oidc_attrs):
        return True
    else:
        # check if non-admin user even has permission to access project-W
        user_role_conf = local_oidc_prov[provider_name].user_role
        if user_role_conf is not None and not has_role(user_role_conf, oidc_attrs):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: Your user lacks the required value for the {user_role_conf.field_name} claim",
                # can't put scope here because if the issuer is unknown we also don't know which scope might be required
                headers={"WWW-Authenticate": "Bearer"},
            )
        return False


async def validate_id_token(id_token: str, iss: str) -> bool:
    """
    Validates the id_token returned by the IdP and returns whether the user is an admin
    """
    assert local_oidc_prov is not {}
    # get current oidc config name
    name = oauth_iss_to_name.get(iss)
    if name is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate token, iss {iss} not known",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await getattr(oauth, name).parse_id_token({"id_token": id_token}, None)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate token for oidc provider '{name}'",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )
    return validate_oidc_attributes(name, user)


async def invalidate_tokens_if_oidc_user_lost_privileges(tokens: list[OidcTokenInfoInternal]):
    for token in tokens:
        oauth_config = oauth_iss_to_config[token.iss]
        ctx = oauth_iss_to_ctx[token.iss]
        token_endpoint = oauth_config["token_endpoint"]
        userinfo_endpoint = oauth_config["userinfo_endpoint"]
        name = oauth_iss_to_name[token.iss]
        oidc_prov = local_oidc_prov[name]

        if token.oidc_refresh_token is None:
            await dp.db.delete_token_of_user(token.user_id, token.id)
            logger.info(
                f"Invalidated token with id {token.id} of OIDC user {token.user_id} because token didn't have refresh token attached to it"
            )
            return

        async with AsyncClient(verify=ctx) as client:
            try:
                data = {
                    "client_id": oidc_prov.client_id,
                    "client_secret": oidc_prov.client_secret.get_secret_value(),
                    "grant_type": "refresh_token",
                    "refresh_token": token.oidc_refresh_token.get_secret_value(),
                    "scope": "openid email",
                }
                token_resp = (
                    (await client.post(token_endpoint, data=data)).raise_for_status().json()
                )
                access_token = token_resp["access_token"]
                new_refresh_token = SecretStr(token_resp["refresh_token"])
                headers = {"Authorization": f"Bearer {access_token}"}
                userinfo_resp = (
                    (await client.get(userinfo_endpoint, headers=headers)).raise_for_status().json()
                )
                is_admin = validate_oidc_attributes(name, userinfo_resp)
                if not is_admin and token.admin_privileges:
                    await dp.db.delete_token_of_user(token.user_id, token.id)
                    logger.info(
                        f"Invalidated admin token with id {token.id} of OIDC user {token.user_id} because user doesn't have admin privileges anymore"
                    )
                updated_tokens = await dp.db.token_replace_oidc_refresh_token(
                    token.oidc_refresh_token, new_refresh_token
                )
                for token in tokens:
                    if token.id in updated_tokens:
                        token.oidc_refresh_token = new_refresh_token
            except (HTTPStatusError, JSONDecodeError):
                await dp.db.delete_token_of_user(token.user_id, token.id)
                logger.info(
                    f"Invalidated token with id {token.id} of OIDC user {token.user_id} because user couldn't be found at OIDC provider with all necessary attributes"
                )
