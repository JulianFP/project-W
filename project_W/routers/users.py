from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

import project_W.dependencies as dp

from ..model import User, UserInDb
from ..security import validate_normal_user

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/info")
async def user_info(current_user: Annotated[UserInDb, Depends(validate_normal_user)]) -> User:
    return current_user


@router.delete("/delete")
async def delete_user(current_user: Annotated[UserInDb, Depends(validate_normal_user)]):
    await dp.db.delete_user(current_user.id)
    return "success!"
