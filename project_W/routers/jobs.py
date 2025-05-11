from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from starlette.status import HTTP_400_BAD_REQUEST

import project_W.dependencies as dp
from project_W.models.internal import JobSortKey

from ..models.request_data import JobSettings
from ..models.response_data import ErrorResponse, User
from ..security.auth import auth_dependency_responses, validate_user_and_get_from_db

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    responses=auth_dependency_responses,
)


@router.post("/submit_settings")
async def submit_settings(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=True, require_admin=False))
    ],
    job_settings: JobSettings,
    is_new_default: bool = False,
) -> int:
    return await dp.db.add_new_job_settings(current_user.id, job_settings, is_new_default)


@router.get("/default_settings")
async def get_default_settings(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=False, require_admin=False))
    ]
) -> JobSettings:
    if (job_settings := await dp.db.get_default_job_settings_of_user(current_user.id)) is not None:
        return job_settings
    else:
        return JobSettings()


@router.post(
    "/submit_job",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Not an audio file or provided job_settings_id was invalid",
        }
    },
)
async def submit_job(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=True, require_admin=False))
    ],
    audio_file: UploadFile,
    job_settings_id: int | None = None,
) -> int:
    if not audio_file.content_type or audio_file.content_type.split("/")[0].strip() not in [
        "audio",
        "video",
    ]:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"The provided file is not an audio or video file but is of type {audio_file.content_type}",
        )

    if (job_id := await dp.db.add_new_job(current_user.id, audio_file, job_settings_id)) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The provided job_settings_id of '{job_settings_id}' is invalid",
        )

    await dp.ch.enqueue_new_job(job_id, 0)
    return job_id


@router.get("/count")
async def job_count(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=True, require_admin=False))
    ],
    exclude_finished: bool,
    exclude_downloaded: bool,
) -> int:
    return await dp.db.get_total_number_of_jobs_of_user(
        current_user.id, exclude_finished, exclude_downloaded
    )


@router.get("/top_k")
async def top_k_jobs(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=True, require_admin=False))
    ],
    k: int,
    sort_key: JobSortKey,
    descending: bool,
    exclude_finished: bool,
    exclude_downloaded: bool,
) -> list[int]:
    return await dp.db.get_top_k_job_ids_of_user(
        current_user.id, k, sort_key, descending, exclude_finished, exclude_downloaded
    )
