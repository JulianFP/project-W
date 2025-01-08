from typing import Annotated

from fastapi import APIRouter, Depends

from ..dependencies import jwt_handler
from ..model import User, UserInDb

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.get("/info")
async def user_info(
    current_user: Annotated[UserInDb, Depends(jwt_handler.get_current_user)]
) -> User:
    return current_user
