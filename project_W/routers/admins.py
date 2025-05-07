from typing import Annotated

from fastapi import APIRouter, Depends

import project_W.dependencies as dp

from ..models.internal import DecodedAuthTokenData
from ..models.response_data import RunnerCreatedInfo
from ..security.auth import auth_dependency_responses, validate_user

router = APIRouter(
    prefix="/admins",
    tags=["admins"],
    # all routes handled by this routes are authenticated
    responses=auth_dependency_responses,
)


@router.post("/create_runner")
async def create_runner(
    _: Annotated[
        DecodedAuthTokenData, Depends(validate_user(require_verified=True, require_admin=True))
    ]
) -> RunnerCreatedInfo:
    return await dp.db.create_runner()


@router.get("/test")
async def admin_test(
    _: Annotated[
        DecodedAuthTokenData, Depends(validate_user(require_verified=False, require_admin=True))
    ]
):
    return "Only an admin is allowed to see this"
