from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

import project_W.dependencies as dp
import project_W.security.oidc_deps as oidc
from project_W.models.base import EmailValidated

from ..models.response_data import ErrorResponse

router = APIRouter(
    prefix="/oidc",
    tags=["oidc"],
)


@router.get("/login/{idp_name}", name="oidc-redirect")
async def login(idp_name: str, request: Request) -> RedirectResponse:
    """
    Start an OIDC login flow. This route will redirect you to the login page of the identity provider 'idp_name'. This name was specified by the admin in the config of this instance. Use the /api/auth_settings route to get the authentication-related configuration of this instance.
    """
    redirect_uri = request.url_for("oidc-auth", idp_name=idp_name)
    idp_name = idp_name.lower()
    return await getattr(oidc.oauth, idp_name).authorize_redirect(request, redirect_uri)


@router.get(
    "/auth/{idp_name}",
    name="oidc-auth",
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
async def auth(idp_name: str, request: Request) -> RedirectResponse:
    """
    Landing route: After authenticating on the login page of the identity provider the provider will redirect you to this route so that the backend can process the IdP's response. This route will then redirect you to the official client's page (as set by the instance's admin) so that the client can get and store the OIDC id_token.
    """
    idp_name = idp_name.lower()
    try:
        oidc_response = await getattr(oidc.oauth, idp_name).authorize_access_token(request)
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
    if not (email := EmailValidated.model_validate(userinfo.get("email"))):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get a valid email address from the identity provider. Please make sure that the IdP supports the email claim, that your account has an email address associated with it and that this email is valid",
        )
    if not (id_token := oidc_response.get("id_token")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not get an id_token from the identity provider",
        )

    # validate id_token before creating user so that possible errors are already displayed here to the user
    # and we don't create accounts in the database for nothing
    # this also verifies email_verified and user_role/admin_role claims
    await oidc.validate_oidc_token(id_token, iss)

    await dp.db.ensure_oidc_user_exists(
        iss,
        sub,
        email,
    )
    return RedirectResponse(f"{dp.config.client_url}/auth/oidc-accept?token={id_token}")
