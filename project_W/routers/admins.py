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


@router.delete("/invalidate_runner")
async def invalidate_runner(
    _: Annotated[
        DecodedAuthTokenData, Depends(validate_user(require_verified=True, require_admin=True))
    ],
    runner_id: int,
) -> str:
    """
    Invalidate the token of a runner and delete it from the database and redis. If it has any jobs assigned at the time of invalidation these jobs will be reassigned to a different runner. Call this route immediately ones you find out that a runner token was compromised!
    """
    if online_runner := await dp.ch.get_online_runner_by_id(runner_id):
        await dp.ch.unregister_online_runner(online_runner.id)

        if online_runner.assigned_job_id is not None:
            user_id = await dp.db.get_user_id_of_job(online_runner.assigned_job_id)
            if user_id is not None:
                await dp.ch.enqueue_new_job(online_runner.assigned_job_id, 0, user_id)

    await dp.db.delete_runner(runner_id)

    return f"If a runner with id {runner_id} existed it was successfully invalidated and deleted"
