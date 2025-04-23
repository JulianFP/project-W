import ssl

import certifi
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from httpx import AsyncClient

import project_W.dependencies as dp
from project_W.models.settings import OidcRoleSettings, Settings

from ..models.internal import DecodedTokenData
from ..models.response_data import ErrorResponse, User

oauth = OAuth()

oauth_iss_to_name = {}


async def register_with_oidc_providers(config: Settings):
    oidc_prov = config.security.oidc_providers
    if oidc_prov is {}:
        raise Exception("Tried to use oidc router even though oidc is disabled in config!")
    for name, idp in oidc_prov.items():
        if idp.ca_pem_file_path:
            cafile = idp.ca_pem_file_path
        else:
            cafile = certifi.where()
        ctx = ssl.create_default_context(cafile=cafile)
        async with AsyncClient(verify=ctx) as client:
            name = name.lower()
            metadata_uri = f"{idp.base_url}/.well-known/openid-configuration"
            oauth.register(
                name,
                client_id=idp.client_id,
                client_secret=idp.client_secret,
                server_metadata_url=metadata_uri,
                client_kwargs={
                    "scope": "openid email",
                    "verify": ctx,
                },
            )

            oidc_config = (await client.get(metadata_uri)).json()
            oauth_iss_to_name[oidc_config["issuer"]] = name


router = APIRouter(
    prefix="/oidc",
    tags=["oidc"],
)


@router.get("/login/{idp_name}", name="Oidc redirect")
async def login(idp_name: str, request: Request) -> RedirectResponse:
    redirect_uri = request.url_for("oidc-auth", idp_name=idp_name)
    idp_name = idp_name.lower()
    return await getattr(oauth, idp_name).authorize_redirect(request, redirect_uri)


@router.get(
    "/auth/{idp_name}",
    name="Oidc auth",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Could not authorize IdP access token",
        },
        401: {
            "model": ErrorResponse,
            "headers": {
                "WWW-Authenticate": {
                    "type": "string",
                }
            },
            "description": "Validation error of id_token",
        },
        403: {
            "model": ErrorResponse,
            "description": "Not enough information or missing scope",
        },
    },
)
async def auth(idp_name: str, request: Request):
    idp_name = idp_name.lower()
    try:
        oidc_response = await getattr(oauth, idp_name).authorize_access_token(request)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authorize IdP access token. Try again from the beginning of the login flow",
        )

    if not (userinfo := oidc_response.get("userinfo")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get any user information from the identity provider",
        )
    if not (iss := userinfo.get("iss")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get iss from the identity provider. Please make sure that the IdP supports the iss claim",
        )
    if not (sub := userinfo.get("sub")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get sub from the identity provider. Please make sure that the IdP supports the sub claim",
        )
    if not (email := userinfo.get("email")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get your email address from the identity provider. Please make sure that the IdP supports the email claim and that your account has an email address associated with it",
        )
    if not (id_token := oidc_response.get("id_token")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get an id_token from the identity provider",
        )

    # validate id_token before creating user so that possible errors are already displayed here to the user
    # and we don't create accounts in the database for nothing
    # this also verifies email_verified and user_role/admin_role claims
    await validate_oidc_token(dp.config, id_token, iss)

    await dp.db.ensure_oidc_user_exists(
        iss,
        sub,
        email,
    )
    return id_token


def has_role(role_conf: OidcRoleSettings, user) -> bool:
    role_name = user.get(role_conf.field_name)
    if isinstance(role_name, list):
        return role_conf.name in role_name
    else:
        return role_name == role_conf.name


async def validate_oidc_token(config: Settings, token: str, iss: str) -> DecodedTokenData:
    oidc_prov = config.security.oidc_providers
    assert oidc_prov is not {}
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
            detail=f"Could not validate token for oidc provider {iss}",
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
    if admin_role_conf is not None and has_role(admin_role_conf, user):
        user["is_admin"] = True
    else:
        user["is_admin"] = False

        # check if non-admin user even has permission to access project-W
        user_role_conf = oidc_prov[name].user_role
        if user_role_conf is not None and not has_role(user_role_conf, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: Your user lacks the required value for the {user_role_conf.field_name} claim",
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication successful, but the user was not found in database",
        )
    return User(
        id=oidc_user.id,
        email=oidc_user.email,
        provider_name=provider_name,
        is_admin=user_token_data.is_admin,
        is_verified=user_token_data.is_verified,
    )
