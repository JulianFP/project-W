from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

import project_W.dependencies as dp

from ..model import Token, User, UserInDb

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post("/login")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = await dp.db.get_user_by_email_checked_password(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    for scope in form_data.scopes:
        if scope == "admin" and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your user isn't an admin",
            )
    access_token = dp.jwt_handler.create_jwt_token(
        data={"sub": user.email, "scopes": form_data.scopes}
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/info")
async def user_info(
    current_user: Annotated[UserInDb, Depends(dp.jwt_handler.get_current_user)]
) -> User:
    return current_user


@router.delete("/delete")
async def delete_user(current_user: Annotated[UserInDb, Depends(dp.jwt_handler.get_current_user)]):
    await dp.db.delete_user(current_user.id)
    return "success!"
