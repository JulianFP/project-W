from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

import project_W.dependencies as dp
import project_W.security.ldap_deps as ldap

from ..models.internal import AuthTokenData
from ..models.response_data import ErrorResponse, UserTypeEnum
from ..security.local_token import create_auth_token

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
async def login(idp_name: str, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> str:
    """
    Log in with an LDAP user queried from the LDAP server with the name 'idp_name'. This name was specified by the admin in the config of this instance. Use the /api/auth_settings route to get the authentication-related configuration of this instance.
    If logging in with an admin account the returned JWT token will not give you admin privileges by default. If you need a token with admin privileges then specify the scope 'admin' during login.
    """

    if not ldap.ldap_adapter.check_idp_name(idp_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not query user, ldap server {idp_name} not known",
        )

    user = await ldap.ldap_adapter.query_user(idp_name, form_data.username)

    if await ldap.ldap_adapter.authenticate_user(idp_name, user.dn, form_data.password):
        user_id = await dp.db.ensure_ldap_user_exists(idp_name, user.dn, user.email)
        data = AuthTokenData(
            user_type=UserTypeEnum.LDAP, sub=str(user_id), email=user.email, is_verified=True
        )
        token = await create_auth_token(dp.config, data, user_id, user.is_admin, form_data.scopes)
        return token
    else:
        raise http_exc
