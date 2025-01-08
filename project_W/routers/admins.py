from typing import Annotated

from fastapi import APIRouter, Security

from ..dependencies import jwt_handler
from ..model import UserInDb

router = APIRouter(
    prefix="/admins",
    tags=["admins"],
)


@router.get("/test")
async def admin_test(
    _: Annotated[UserInDb, Security(jwt_handler.get_current_user, scopes=["admin"])]
):
    return "Only an admin is allowed to see this"
