from typing import Annotated

from fastapi import APIRouter, Depends

from ..models.internal import DecodedAuthTokenData
from ..security.auth import auth_dependency_responses, validate_user

router = APIRouter(
    prefix="/admins",
    tags=["admins"],
    # all routes handled by this routes are authenticated
    responses=auth_dependency_responses,
)


@router.get("/test")
async def admin_test(
    _: Annotated[DecodedAuthTokenData, Depends(validate_user(require_admin=True))]
):
    return "Only an admin is allowed to see this"
