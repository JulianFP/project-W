from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

import project_W.dependencies as dp

from ..models.internal import OnlineRunner
from ..models.request_data import (
    HeartbeatRequest,
    RunnerRegisterRequest,
    RunnerSubmitResultRequest,
)
from ..models.response_data import (
    ErrorResponse,
    HeartbeatResponse,
    RunnerJobInfoResponse,
)
from ..security.auth import (
    auth_dependency_responses,
    validate_online_runner,
    validate_runner,
)

router = APIRouter(
    prefix="/runners",
    tags=["runners"],
    responses=auth_dependency_responses,
)


@router.post(
    "/register",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Runner already registered",
        }
    },
)
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
    if (await dp.ch.get_online_runner_by_id(runner_id)) is not None:
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
        user_id = await dp.db.get_user_id_of_job(job_id)
        if user_id is None:
            raise Exception(
                f"Redis/Postgresql data mismatch: Popped job with id {job_id} from redis that doesn't exist in Postgresql!"
            )
        await dp.ch.assign_job_to_online_runner(job_id, user_id)

    return runner_id


@router.post("/unregister")
async def unregister_runner(
    online_runner: Annotated[OnlineRunner, Depends(validate_online_runner)],
) -> str:
    """
    Unregisters an online runner.
    """
    await dp.ch.unregister_online_runner(online_runner.id)

    if online_runner.assigned_job_id is not None:
        user_id = await dp.db.get_user_id_of_job(online_runner.assigned_job_id)
        if user_id is None:
            raise Exception(
                f"Redis/Postgresql data mismatch: Runner had job {online_runner.assigned_job_id} assigned that doesn't exist in Postgresql!"
            )
        await dp.ch.enqueue_new_job(online_runner.assigned_job_id, 0, user_id)

    return "Success"


@router.get(
    "/retrieve_job_info",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "No job assigned or job not in database",
        },
    },
)
async def retrieve_job_info(
    online_runner: Annotated[OnlineRunner, Depends(validate_online_runner)],
) -> RunnerJobInfoResponse:
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
    return RunnerJobInfoResponse(id=online_runner.assigned_job_id, settings=job_settings)


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
    online_runner: Annotated[OnlineRunner, Depends(validate_online_runner)],
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
            online_runner.id, {"in_process_job_id": online_runner.assigned_job_id}
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
    background_tasks: BackgroundTasks,
) -> str:
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

    if not (settings := await dp.db.get_job_settings_by_job_id(online_runner.in_process_job_id)):
        raise Exception("Trying to submit job with an non-existing id!")
    if not (in_process_job := await dp.ch.get_in_process_job(online_runner.in_process_job_id)):
        raise Exception("Trying to submit job that doesn't exist in Redis!")
    if not (user := await dp.db.get_user_by_id(in_process_job.user_id)):
        raise Exception("Trying to submit a job that belongs to a non-existing user!")

    if submitted_data.error_msg is not None:
        await dp.db.finish_failed_job(
            online_runner.in_process_job_id, submitted_data.error_msg, online_runner
        )
        if settings.email_notification:
            background_tasks.add_task(
                dp.smtp.send_job_failed_email,
                user.email,
                in_process_job.id,
                submitted_data.error_msg,
                dp.config.client_url,
            )
    elif submitted_data.transcript is not None:
        await dp.db.finish_successful_job(online_runner, submitted_data.transcript)
        if settings.email_notification:
            background_tasks.add_task(
                dp.smtp.send_job_success_email, user.email, in_process_job.id, dp.config.client_url
            )
    else:
        raise Exception(
            "Pydantic model validation failed, job submission has neither error_msg nor a transcript attached to it"
        )

    await dp.ch.finish_job_of_online_runner(online_runner)

    # If there are any jobs in the queue, assign one to this runner.
    # TODO: Maybe encapsulate this in a method?
    if (await dp.ch.number_of_enqueued_jobs()) > 0:
        job_id = await dp.ch.pop_job_with_highest_priority()
        if job_id is None:
            raise Exception("Redis data error: job queue is not empty but popmax returns None")
        user_id = await dp.db.get_user_id_of_job(job_id)
        if user_id is None:
            raise Exception(
                f"Redis/Postgresql data mismatch: Popped job with id {job_id} from redis that doesn't exist in Postgresql!"
            )
        await dp.ch.assign_job_to_online_runner(job_id, user_id)

    return "Success"


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
