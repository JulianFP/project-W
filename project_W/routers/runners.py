from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

import project_W.dependencies as dp

from ..models.internal import JobInDb, OnlineRunner
from ..models.request_data import (
    HeartbeatRequest,
    JobSettings,
    RunnerRegisterRequest,
    RunnerSubmitResultRequest,
)
from ..models.response_data import ErrorResponse, HeartbeatResponse, JobStatus
from ..security.auth import (
    auth_dependency_responses,
    validate_online_runner,
    validate_runner,
)


async def load_jobs_from_db():
    """
    Enqueues all jobs from the database that are not finished yet.
    We do not need to check if it already is in the queue since enqueue_job
    already does that (-> no mutex needed for this method)
    Currently, this is only called once just after the server startup
    """
    for job_id in await dp.db.get_all_ids_of_unfinished_jobs():
        await dp.ch.enqueue_new_job(job_id, 0)


async def job_status(job: JobInDb) -> JobStatus:
    if job.downloaded:
        return JobStatus.DOWNLOADED
    if job.transcript is not None:
        return JobStatus.SUCCESS
    if job.error_msg is not None:
        return JobStatus.FAILED
    if (await dp.ch.get_job_pos_in_queue(job.id)) is not None:
        return JobStatus.PENDING_RUNNER
    if (runner_id := (await dp.ch.get_online_runner_by_assigned_job(job.id))) is not None and (
        runner := await dp.ch.get_online_runner_by_id(runner_id)
    ) is not None:
        if runner.in_process_job_id is not None:
            return JobStatus.RUNNER_IN_PROGRESS
        return JobStatus.RUNNER_ASSIGNED
    # TODO: Do we need additional logic here?
    return JobStatus.NOT_QUEUED


async def status_dict(job: JobInDb) -> dict[str, str | int | float]:
    data: dict[str, str | int | float] = {"step": (await job_status(job)).value}
    if (runner_id := (await dp.ch.get_online_runner_by_assigned_job(job.id))) is not None and (
        runner := await dp.ch.get_online_runner_by_id(runner_id)
    ) is not None:
        data["runner"] = runner.id
        if runner.in_process_job_id is not None:
            if runner.assigned_job_id is None:
                raise Exception(
                    f"Redis data invalid: in_process_job of runner {runner_id} is set but assigned_job_id is None"
                )
            data["progress"] = runner.assigned_job_id
    return data


async def abort_job(job: JobInDb):
    jobStatus = job_status(job)
    assert (
        jobStatus is not JobStatus.SUCCESS or JobStatus.FAILED or JobStatus.DOWNLOADED
    ), "you cannot abort a job that has already run!"
    if jobStatus is JobStatus.NOT_QUEUED:
        job.error_msg = "Job was aborted"
    elif jobStatus is JobStatus.PENDING_RUNNER:
        await dp.ch.remove_job_from_queue(job.id)
        job.error_msg = "Job was aborted"
    elif jobStatus is JobStatus.RUNNER_ASSIGNED or JobStatus.RUNNER_IN_PROGRESS:
        await dp.ch.set_in_process_job(job.id, {"abort": 1})


router = APIRouter(
    prefix="/runners",
    tags=["runners"],
    responses=auth_dependency_responses,
)


@router.post("/register")
async def register(
    runner_id: Annotated[int, Depends(validate_runner)],
    runner_data: RunnerRegisterRequest,
) -> int:
    """
    Registers the given runner as online. Returns False if the
    runner is already registered as online or True otherwise.
    Starting from the registration, the runner must periodically send
    heartbeat requests to the manager, or it may be unregistered.
    """
    if dp.ch.get_online_runner_by_id(runner_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This runner is already registered as online!",
        )

    online_runner = OnlineRunner.model_validate(runner_data.model_dump() | {"id": runner_id})
    await dp.ch.register_new_online_runner(online_runner)

    # TODO: If we have runner tags, only assign job if it has the right tag.
    if (await dp.ch.number_of_enqueued_jobs()) > 0:
        job_id = await dp.ch.pop_job_with_highest_priority()
        if job_id is None:
            raise Exception("Redis data error: job queue is not empty but popmax returns None")
        await dp.ch.assign_job_to_online_runner(job_id)

    return runner_id


@router.post("/unregister")
async def unregister_runner(
    online_runner: Annotated[OnlineRunner, Depends(validate_online_runner)]
):
    """
    Unregisters an online runner.
    """
    await dp.ch.unregister_online_runner(online_runner.id)

    if online_runner.assigned_job_id is not None:
        await dp.ch.enqueue_new_job(online_runner.assigned_job_id, 0)


@router.get(
    "/retrieve_job_info",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "No job assigned",
        },
    },
)
async def retrieve_job_info(
    online_runner: Annotated[OnlineRunner, Depends(validate_online_runner)]
) -> JobSettings:
    if online_runner.assigned_job_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This runner has currently no job assigned",
        )
    if (
        job_settings := await dp.db.get_job_settings_by_job_id(online_runner.assigned_job_id)
    ) is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The job id of this runner doesn't appear in the database!",
        )
    return job_settings


@router.post(
    "/retrieve_job_audio",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "No job assigned",
        },
    },
)
async def retrieve_job_audio(
    online_runner: Annotated[OnlineRunner, Depends(validate_online_runner)]
) -> StreamingResponse:
    """
    For a given online runner, retrieves the job that it has been assigned.
    Additionally, if the runner wasn't marked as processing the job yet, it
    marks it as such. If the runner has not been assigned a job, it returns
    None and does nothing.
    """
    if online_runner.assigned_job_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This runner has currently no job assigned",
        )

    if online_runner.in_process_job_id is None:
        await dp.ch.set_online_runner(
            online_runner.id, {"in_process_job": online_runner.assigned_job_id}
        )

    return StreamingResponse(
        dp.db.get_job_audio(online_runner.assigned_job_id), media_type="audio/"
    )


@router.post(
    "/submit_job_result",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Runner not processing a job",
        },
    },
)
async def submit_job_result(
    online_runner: Annotated[OnlineRunner, Depends(validate_online_runner)],
    submitted_data: RunnerSubmitResultRequest,
):
    """
    Handles the submission of a job result by a runner. If the runner is not currently
    processing a job, returns an error message. Otherwise, marks the job as completed/failed
    by setting either the transcript or the error_msg field of the job, marks the runner as
    available and returns None.
    """
    if online_runner.in_process_job_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This runner is currently not processing a job!",
        )

    if submitted_data.error:
        await dp.db.finish_failed_job(online_runner, submitted_data.result)
    else:
        await dp.db.finish_successful_job(online_runner, submitted_data.result)

    await dp.ch.finish_job_of_online_runner(online_runner)

    # If there are any jobs in the queue, assign one to this runner.
    # TODO: Maybe encapsulate this in a method?
    if (await dp.ch.number_of_enqueued_jobs()) > 0:
        job_id = await dp.ch.pop_job_with_highest_priority()
        if job_id is None:
            raise Exception("Redis data error: job queue is not empty but popmax returns None")
        await dp.ch.assign_job_to_online_runner(job_id)


@router.post("/heartbeat")
async def heartbeat(
    online_runner: Annotated[OnlineRunner, Depends(validate_online_runner)], req: HeartbeatRequest
) -> HeartbeatResponse:
    await dp.ch.reset_runner_expiration(online_runner.id)

    if online_runner.in_process_job_id is not None:
        in_process_job = await dp.ch.get_in_process_job(online_runner.in_process_job_id)
        if in_process_job is None:
            raise Exception(
                "Redis data invalid: OnlineRunner has in_process_job set but the jobs key doesn't exist"
            )
        if in_process_job.abort:
            return HeartbeatResponse(abort=True)
        await dp.ch.set_in_process_job(online_runner.in_process_job_id, {"progress": req.progress})
    if online_runner.assigned_job_id:
        return HeartbeatResponse(job_assigned=True)
    return HeartbeatResponse()
