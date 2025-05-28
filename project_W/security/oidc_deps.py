import ssl
from json.decoder import JSONDecodeError

import certifi
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from httpx import AsyncClient, HTTPError, HTTPStatusError

import project_W.dependencies as dp
from project_W.logger import get_logger
from project_W.models.settings import OidcProviderSettings, OidcRoleSettings, Settings

from ..models.internal import DecodedAuthTokenData
from ..models.response_data import User, UserTypeEnum

oauth = OAuth()

oauth_iss_to_name = {}
oauth_iss_to_nice_name = {}
local_oidc_prov: dict[str, OidcProviderSettings] = (
    {}
)  # local copy of settings with normalized provider names

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
            oauth_iss_to_nice_name[oidc_config["issuer"]] = name
            oauth_iss_to_name[oidc_config["issuer"]] = norm_name
        logger.info(f"Connected with OIDC provider {name}")


def has_role(role_conf: OidcRoleSettings, user) -> bool:
    role_name = user.get(role_conf.field_name)
    if isinstance(role_name, list):
        return role_conf.name in role_name
    else:
        return role_name == role_conf.name


async def validate_oidc_token(token: str, iss: str) -> DecodedAuthTokenData:
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
        user = await getattr(oauth, name).parse_id_token({"id_token": token}, None)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate token for oidc provider '{name}'",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The email address of this OIDC '{name}' account is not verified",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )
    user["is_verified"] = True
    user["user_type"] = UserTypeEnum.OIDC

    # check if user is admin
    admin_role_conf = local_oidc_prov[name].admin_role
    if admin_role_conf is not None and has_role(admin_role_conf, user):
        user["is_admin"] = True
    else:
        user["is_admin"] = False

        # check if non-admin user even has permission to access project-W
        user_role_conf = local_oidc_prov[name].user_role
        if user_role_conf is not None and not has_role(user_role_conf, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: Your user lacks the required value for the {user_role_conf.field_name} claim",
                # can't put scope here because if the issuer is unknown we also don't know which scope might be required
                headers={"WWW-Authenticate": "Bearer"},
            )

    return DecodedAuthTokenData.model_validate(user)


async def lookup_oidc_user_in_db_from_token(user_token_data: DecodedAuthTokenData) -> User:
    oidc_user = await dp.db.get_oidc_user_by_iss_sub(user_token_data.iss, user_token_data.sub)
    if not oidc_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication successful, but the user was not found in database",
        )
    provider_name = oauth_iss_to_nice_name.get(oidc_user.iss)
    if not provider_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication successful, but the user was not found in database",
        )
    return User(
        id=oidc_user.id,
        user_type=UserTypeEnum.OIDC,
        email=oidc_user.email,
        provider_name=provider_name,
        is_admin=user_token_data.is_admin,
        is_verified=user_token_data.is_verified,
    )


async def lookup_oidc_user_in_db_from_api_token(user_token_data: DecodedAuthTokenData) -> User:
    oidc_user = await dp.db.get_oidc_user_by_id(int(user_token_data.sub))
    if not oidc_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication successful, but the user was not found in database",
        )
    provider_name = oauth_iss_to_nice_name.get(oidc_user.iss)
    if not provider_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication successful, but the user was not found in database",
        )
    return User(
        id=oidc_user.id,
        user_type=UserTypeEnum.OIDC,
        email=oidc_user.email,
        provider_name=provider_name,
        is_admin=user_token_data.is_admin,
        is_verified=user_token_data.is_verified,
    )
