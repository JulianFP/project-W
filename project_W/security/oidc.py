from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from httpx import AsyncClient

import project_W.dependencies as dp
from project_W.models.settings import Settings

from ..models.internal import DecodedTokenData
from ..models.response_data import User

oauth = OAuth()

oauth_iss_to_name = {}


async def register_with_oidc_providers(config: Settings):
    oidc_prov = config.security.oidc_providers
    async with AsyncClient() as client:
        if oidc_prov is {}:
            raise Exception("Tried to use oidc router even though oidc is disabled in config!")
        for name, idp in oidc_prov.items():
            name = name.lower()
            metadata_uri = f"{idp.base_url}/.well-known/openid-configuration"
            oauth.register(
                name,
                client_id=idp.client_id,
                client_secret=idp.client_secret,
                server_metadata_url=metadata_uri,
                client_kwargs={"scope": "openid email"},
            )

            oidc_config = (await client.get(metadata_uri)).json()
            oauth_iss_to_name[oidc_config["issuer"]] = name


router = APIRouter(
    prefix="/oidc",
    tags=["oidc"],
)


@router.get("/login/{idp_name}")
async def login(idp_name: str, request: Request) -> RedirectResponse:
    redirect_uri = request.url_for("oidc-auth", idp_name=idp_name)
    idp_name = idp_name.lower()
    return await getattr(oauth, idp_name).authorize_redirect(request, redirect_uri)


@router.get("/auth/{idp_name}", name="oidc-auth")
async def auth(idp_name: str, request: Request) -> JSONResponse:
    idp_name = idp_name.lower()
    oidc_response = await getattr(oauth, idp_name).authorize_access_token(request)
    user_created = await dp.db.add_new_oidc_user(
        oidc_response["userinfo"]["iss"],
        oidc_response["userinfo"]["sub"],
        oidc_response["userinfo"]["email"],
    )
    return JSONResponse(
        {
            "token": oidc_response["id_token"],
            "created": user_created,
        }
    )


async def validate_oidc_token(config: Settings, token: str, iss: str) -> DecodedTokenData:
    oidc_prov = config.security.oidc_providers
    assert oidc_prov is not {}
    # get current oidc config name
    name = oauth_iss_to_name.get(iss)
    if name is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials, iss {iss} not known",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await getattr(oauth, name).parse_id_token({"id_token": token}, None)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials for oidc provider {iss}",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The email address of this OIDC {iss} account is not verified",
            # can't put scope here because if the issuer is unknown we also don't know which scope might be required
            headers={"WWW-Authenticate": "Bearer"},
        )
    user["is_verified"] = True

    # check if user is admin
    admin_role_conf = oidc_prov[name].admin_role
    if admin_role_conf is not None and user[admin_role_conf.field_name] == admin_role_conf.name:
        user["is_admin"] = True
    else:
        user["is_admin"] = False

        # check if non-admin user even has permission to access project-W
        user_role_conf = oidc_prov[name].user_role
        if user_role_conf is not None and user[user_role_conf.field_name] != user_role_conf.name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions",
                # can't put scope here because if the issuer is unknown we also don't know which scope might be required
                headers={"WWW-Authenticate": "Bearer"},
            )

    return DecodedTokenData.model_validate(user)


async def lookup_oidc_user_in_db_from_token(user_token_data: DecodedTokenData) -> User:
    oidc_user = await dp.db.get_oidc_user_by_iss_sub(user_token_data.iss, user_token_data.sub)
    if not oidc_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication successful, but the user was not found in database",
        )
    provider_name = oauth_iss_to_name.get(oidc_user.iss)
    if not provider_name:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication successful, but the user was not found in database",
        )
    return User(
        id=oidc_user.id,
        email=oidc_user.email,
        provider_name=provider_name,
        is_admin=user_token_data.is_admin,
        is_verified=user_token_data.is_verified,
    )
