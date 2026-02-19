from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from project_W_lib.models.response_models import ErrorResponse

import project_W.dependencies as dp
import project_W.security.ldap_deps as ldap

from ..security.auth import check_admin_privileges, set_token_cookie

router = APIRouter(
    prefix="/ldap",
    tags=["ldap"],
)

http_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
)


@router.post(
    "/login/{idp_name}",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "idp_name is invalid",
        },
        401: {"model": ErrorResponse, "description": "Authentication was unsuccessful"},
    },
)
async def login(
    idp_name: str,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    user_agent: Annotated[str | None, Header()] = None,
) -> str:
    """
    Log in with an LDAP user queried from the LDAP server with the name 'idp_name'. This name was specified by the admin in the config of this instance. Use the /api/auth_settings route to get the authentication-related configuration of this instance.
    If logging in with an admin account the returned auth token will not give you admin privileges by default. If you need a token with admin privileges then specify the scope 'admin' during login.
    """

    if not ldap.ldap_adapter.check_idp_name(idp_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not query user, ldap server {idp_name} not known",
        )

    user = await ldap.ldap_adapter.query_user_with_username(idp_name, form_data.username)

    if await ldap.ldap_adapter.authenticate_user(idp_name, user.dn, form_data.password):
        user_id = await dp.db.ensure_ldap_user_exists(idp_name, user.uid, user.email)

        admin_privileges = check_admin_privileges(form_data.scopes, user.is_admin)
        if user_agent is None:
            token_name = "Unknown device"
        else:
            token_name = user_agent

        token = await dp.db.add_new_user_token(
            user_id,
            token_name,
            False,
            admin_privileges,
            dp.config.security.tokens.session_expiration_time_minutes,
        )
        set_token_cookie(response, token)
        return "Success. Returning your login token as a cookie"
    else:
        raise http_exc
