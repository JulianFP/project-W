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
    ],
) -> RunnerCreatedInfo:
    """
    Create a new global runner that can be used by all users of this instance. Returns the id and the runner token of the newly created runner. Put this token into the config file of the runner that you are trying to host. Create a new runner token for each new runner that you want to host using this route!
    """
    return await dp.db.create_runner()
