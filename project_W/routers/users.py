from typing import Annotated

from fastapi import APIRouter, Depends

import project_W.dependencies as dp
from project_W.models.response_data import User

from ..models.internal import DecodedTokenData
from ..security.auth import (
    auth_dependency_responses,
    validate_user,
    validate_user_and_get_from_db,
)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses=auth_dependency_responses,
)


@router.get("/info")
async def user_info(
    current_token: Annotated[DecodedTokenData, Depends(validate_user(require_admin=False))]
) -> DecodedTokenData:
    return current_token


@router.delete("/delete")
async def delete_user(
    current_user: Annotated[User, Depends(validate_user_and_get_from_db(require_admin=False))]
):
    await dp.db.delete_user(current_user.id)
    return "success!"
