from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST

import project_W.dependencies as dp
from project_W.models.internal import JobAndSettingsInDb, JobInDb, JobSortKey

from ..models.request_data import JobSettings, TranscriptTypeEnum
from ..models.response_data import (
    ErrorResponse,
    JobInfo,
    JobStatus,
    User,
)
from ..security.auth import auth_dependency_responses, validate_user_and_get_from_db


async def job_status(job: JobInDb) -> JobStatus:
    if job.downloaded:
        return JobStatus.DOWNLOADED
    if job.downloaded is not None:
        return JobStatus.SUCCESS
    if job.error_msg is not None:
        return JobStatus.FAILED
    if job.aborting:
        return JobStatus.ABORTING
    if (runner_id := (await dp.ch.get_online_runner_id_by_assigned_job(job.id))) is not None and (
        runner := await dp.ch.get_online_runner_by_id(runner_id)
    ) is not None:
        if runner.in_process:
            return JobStatus.RUNNER_IN_PROGRESS
        return JobStatus.RUNNER_ASSIGNED
    if await dp.ch.queue_contains_job(job.id):
        return JobStatus.PENDING_RUNNER
    # TODO: Do we need additional logic here?
    return JobStatus.NOT_QUEUED


router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    responses=auth_dependency_responses,
)


@router.post("/submit_settings")
async def submit_settings(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
    job_settings: JobSettings,
    is_new_default: bool = False,
) -> int:
    """
    Submit a new job settings object to the backend. If is_new_default is set to True this set of job settings will become the new default for this account and if no job settings object is specified during job submission this set of settings will be used. If it is set to False then this set of settings will only be used if specified explicitly during job submission. Returns the id of the newly created job settings object which can then be used to reference these job settings during job submission.
    """
    return await dp.db.add_new_job_settings(current_user.id, job_settings, is_new_default)


@router.get("/default_settings")
async def get_default_settings(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=False, require_admin=False, require_tos=False
            )
        ),
    ],
) -> JobSettings:
    """
    Returns the default job settings of the current account. If no job settings id is explicitly specified during job submission then these job settings will be used for the job. These job settings where either set previously using the submit_settings route or are the application defaults.
    """
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
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
    audio_file: UploadFile,
    job_settings_id: int | None = None,
) -> int:
    """
    Submit a new transcription job. If the job_settings_id is omitted the account defaults will be used.
    If you want to define the job settings then create a job settings object using the submit_settings route and then set job_settings_id here to the returned integer.
    Returns the id of the newly created job.
    """
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

    await dp.ch.enqueue_new_job(job_id, job_id * -1)
    await dp.ch.assign_queue_job_to_runner_if_possible()
    return job_id


@router.get("/count")
async def job_count(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
    exclude_finished: bool,
    exclude_downloaded: bool,
) -> int:
    """
    Returns the total amount of jobs this user has after applying the provided filter options.
    exclude_finished excludes finished jobs (both successful and aborted) while exclude_downloaded excludes finished jobs where the transcript was already downloaded at least ones.
    """
    return await dp.db.get_total_number_of_jobs_of_user(
        current_user.id, exclude_finished, exclude_downloaded
    )


@router.get("/get")
async def get(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
    start_index: int,
    end_index: int,
    sort_key: JobSortKey,
    descending: bool,
    exclude_finished: bool,
    exclude_downloaded: bool,
) -> list[int]:
    """
    Returns a list of job ids sorted and filtered by the specified criteria.
    start_index and end_index specify which jobs to return from the sorted list, e.g. a start_index of 0 and end_index of 9 will return the first 10 jobs, while a start_index of 10 and and end_index of 19 will return the next 10 and so on.
    """
    return await dp.db.get_job_ids_of_user(
        current_user.id,
        start_index,
        end_index,
        sort_key,
        descending,
        exclude_finished,
        exclude_downloaded,
    )


@router.get("/info")
async def job_info(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
    job_ids: Annotated[list[int], Query()],
) -> list[JobInfo]:
    """
    Returns a list of job objects containing all information related to each of the specified jobs.
    Note that job infos will be returned in no specific order, please use the get route to get an ordering of jobs by id and only use this route to get additional information about these jobs.
    """
    job_and_setting_infos: list[JobAndSettingsInDb] = (
        await dp.db.get_job_infos_with_settings_of_user(current_user.id, job_ids)
    )
    job_infos = []
    for job in job_and_setting_infos:
        data = job.model_dump()  # JobAndSettings
        data["step"] = await job_status(job)  # step
        if (in_process_job := await dp.ch.get_in_process_job(job.id)) is not None:
            data = data | in_process_job.model_dump()  # InProcessJobBase
            if (
                runner_id := (await dp.ch.get_online_runner_id_by_assigned_job(job.id))
            ) is not None and (
                runner := await dp.ch.get_online_runner_by_id(runner_id)
            ) is not None:
                runner_dict = runner.model_dump()
                for key, val in runner_dict.items():
                    data[f"runner_{key}"] = val  # JobBase optional data
        elif data["step"] in [JobStatus.SUCCESS, JobStatus.DOWNLOADED, JobStatus.ABORTING]:
            data["progress"] = 100
        job_infos.append(JobInfo.model_validate(data))
    return job_infos


@router.post(
    "/abort",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least one of jobs is not running",
        }
    },
)
async def abort_jobs(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
    job_ids: list[int],
) -> str:
    """
    Aborts a currently running job. This will put the job into a failed state with an error message saying that the job was aborted. Any processing of this job will be canceled.
    """
    jobs: list[JobInDb] = await dp.db.get_job_infos_of_user(current_user.id, job_ids)
    for job in jobs:
        jobStatus = await job_status(job)
        if jobStatus in [
            JobStatus.SUCCESS,
            JobStatus.FAILED,
            JobStatus.DOWNLOADED,
            JobStatus.ABORTING,
        ]:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="At least one of the provided jobs is currently not running",
            )

    # second loop because first loop ensures that all jobs are valid first
    for job in jobs:
        jobStatus = await job_status(job)
        if jobStatus in [JobStatus.RUNNER_ASSIGNED, JobStatus.RUNNER_IN_PROGRESS]:
            await dp.db.mark_job_as_aborting(job.id)
            await dp.ch.abort_in_process_job(job.id)
        else:
            if jobStatus is JobStatus.PENDING_RUNNER:
                await dp.ch.remove_job_from_queue(job.id)
            await dp.db.finish_failed_job(job.id, "Job was aborted")

    return "Success"


@router.delete(
    "/delete",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least one of jobs is running",
        }
    },
)
async def delete_jobs(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
    job_ids: list[int],
) -> str:
    """
    Deletes a completed (aborted/successfully finished) job. To delete a currently running job please use the abort route first and then delete it using this route.
    """
    jobs: list[JobInDb] = await dp.db.get_job_infos_of_user(current_user.id, job_ids)
    for job in jobs:
        jobStatus = await job_status(job)
        if jobStatus not in [JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.DOWNLOADED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The job with id {job.id} is currently still running. Only finished jobs can be deleted!",
            )

    await dp.db.delete_jobs_of_user(current_user.id, job_ids)

    return "Success"


@router.get(
    "/download_transcript",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "No job with that id exists or that job isn't finished",
        }
    },
)
async def download_transcript(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
    job_id: int,
    transcript_type: TranscriptTypeEnum,
) -> str | dict:
    """
    Downloads the transcript of a successfully finished job. The transcript can be downloaded in multiple formats.
    Returns the transcript as a string.
    """
    if (
        transcript := await dp.db.get_job_transcript_of_user_set_downloaded(
            current_user.id, job_id, transcript_type
        )
    ) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No job with id {job_id} found or job isn't finished yet",
        )
    else:
        return transcript


@router.get("/events")
async def events(
    current_user: Annotated[
        User,
        Depends(
            validate_user_and_get_from_db(
                require_verified=True, require_admin=False, require_tos=True
            )
        ),
    ],
) -> StreamingResponse:
    """
    This is a special route for subscribing to server-sent events (SSE).
    Currently there is only one type of event called 'job_updated'. It returns the job id of a currently running job which attributes (e.g. processing step, progress, assigned runner, ...) have changed. This event can be used to only fetch job info using the info route when it actually has changed without having to periodically re-fetch the job info of all jobs.
    """
    return StreamingResponse(dp.ch.event_generator(current_user.id), media_type="text/event-stream")
