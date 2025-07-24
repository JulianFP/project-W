from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

import project_W.dependencies as dp
from project_W.models.request_data import EmailToUsers, SiteBanner

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

    await dp.db.delete_runner(runner_id)

    return f"If a runner with id {runner_id} existed it was successfully invalidated and deleted"


@router.post("/add_site_banner")
async def add_site_banner(
    _: Annotated[
        DecodedAuthTokenData, Depends(validate_user(require_verified=True, require_admin=True))
    ],
    banner_info: SiteBanner,
) -> int:
    """
    Add a new banner to the website that will be broadcasted to all users. Returns the id of the created banner.
    Banners with higher urgency will be displayed first. The text of a banner with an urgency between 100 and 200 (excluding) will be highlighted in red. Banners with an urgency of 200 and more will have a red background.
    """
    if banner_id := await dp.db.add_site_banner(banner_info.urgency, banner_info.html):
        return banner_id
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Site banner creation failed with a database error",
        )


@router.delete("/delete_site_banner")
async def delete_site_banner(
    _: Annotated[
        DecodedAuthTokenData, Depends(validate_user(require_verified=True, require_admin=True))
    ],
    banner_id: int,
):
    await dp.db.delete_site_banner(banner_id)


@router.post("/send_email_to_all_users")
async def send_email_to_all_users(
    _: Annotated[
        DecodedAuthTokenData, Depends(validate_user(require_verified=True, require_admin=True))
    ],
    background_tasks: BackgroundTasks,
    email: EmailToUsers,
):
    """
    Sends out an email with the provided content to all users of this Project-W instance, regardless whether they are local accounts, oidc accounts or ldap accounts. The body is in plaintext format, don't forget to include line breaks for longer emails.
    """
    user_emails = await dp.db.get_all_user_emails()
    background_tasks.add_task(
        dp.smtp.send_email,
        user_emails,
        "broadcast",
        email.subject,
        email.body,
    )
