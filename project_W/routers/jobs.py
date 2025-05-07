from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

import project_W.dependencies as dp

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


@router.get("/get_default_settings")
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
            "description": "Provided job_settings_id was invalid",
        }
    },
)
async def submit_job(
    current_user: Annotated[
        User, Depends(validate_user_and_get_from_db(require_verified=True, require_admin=False))
    ],
    audio_file: Annotated[UploadFile, File()],
    job_settings_id: Annotated[int | None, Form()] = None,
) -> int:
    if (job_id := await dp.db.add_new_job(current_user.id, audio_file, job_settings_id)) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The provided job_settings_id of '{job_settings_id}' is invalid",
        )
    else:
        return job_id
