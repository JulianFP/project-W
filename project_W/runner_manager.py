import project_W.dependencies as dp
from project_W.logger import get_logger

from .caching import CachingAdapter
from .models.internal import InProcessJob, JobInDb, JobStatus, OnlineRunner
from .models.request_data import HeartbeatRequest
from .models.response_data import HeartbeatResponse

logger = get_logger("project-W")


class RunnerManager:
    """
    This class represents the runner manager and job scheduler of the server.
    It keeps track of which runners are currently registered as online, processes
    runner heartbeats, schedules and dispatches jobs to their runners and retrieves
    the job results.
    """

    ch: CachingAdapter

    def __init__(self, caching_adapter: CachingAdapter):
        self.ch = caching_adapter

    async def load_jobs_from_db(self):
        """
        Enqueues all jobs from the database that are not finished yet.
        We do not need to check if it already is in the queue since enqueue_job
        already does that (-> no mutex needed for this method)
        Currently, this is only called once just after the server startup
        """
        for job_id in await dp.db.get_all_ids_of_unfinished_jobs():
            await self.enqueue_job(job_id)

    async def is_runner_online(self, runner_id: int) -> bool:
        """
        Returns whether the given runner is currently registered as online.
        """
        return (await self.ch.get_online_runner_by_id(runner_id)) is not None

    async def register_runner(self, runner: OnlineRunner) -> bool:
        """
        Registers the given runner as online. Returns False if the
        runner is already registered as online or True otherwise.
        Starting from the registration, the runner must periodically send
        heartbeat requests to the manager, or it may be unregistered.
        """
        if self.is_runner_online(runner.id):
            logger.info(f"Runner {runner.id} was already online!")
            return False
        await self.ch.register_new_online_runner(runner)
        logger.info(f"Runner {runner.id} just came online!")

        # TODO: If we have runner tags, only assign job if it has the right tag.
        if (await self.ch.number_of_enqueued_jobs()) > 0:
            job_id = await self.ch.pop_job_with_highest_priority()
            if job_id is None:
                raise Exception("Redis data error: job queue is not empty but popmax returns None")
            await self.ch.assign_job_to_online_runner(job_id)

        return True

    async def unregister_runner(self, online_runner: OnlineRunner) -> bool:
        """
        Unregisters an online runner.
        """
        if not await self.is_runner_online(online_runner.id):
            logger.info(f"Runner {online_runner.id} was not online!")
            return False
        await self.ch.unregister_online_runner(online_runner.id)
        logger.info(f"Runner {online_runner.id} just went offline!")

        if online_runner.assigned_job_id is not None:
            logger.info(
                f"  -> Runner was unregistered while still processing a job! Enqueuing job again."
            )
            await self.enqueue_job(online_runner.assigned_job_id)
        return True

    async def job_status(self, job: JobInDb) -> JobStatus:
        if job.downloaded:
            return JobStatus.DOWNLOADED
        if job.transcript is not None:
            return JobStatus.SUCCESS
        if job.error_msg is not None:
            return JobStatus.FAILED
        if (await self.ch.get_job_pos_in_queue(job.id)) is not None:
            return JobStatus.PENDING_RUNNER
        if (
            runner_id := (await self.ch.get_online_runner_by_assigned_job(job.id))
        ) is not None and (runner := await self.ch.get_online_runner_by_id(runner_id)) is not None:
            if runner.in_process_job_id is not None:
                return JobStatus.RUNNER_IN_PROGRESS
            return JobStatus.RUNNER_ASSIGNED
        # TODO: Do we need additional logic here?
        return JobStatus.NOT_QUEUED

    async def status_dict(self, job: JobInDb) -> dict[str, str | int | float]:
        data: dict[str, str | int | float] = {"step": (await self.job_status(job)).value}
        if (
            runner_id := (await self.ch.get_online_runner_by_assigned_job(job.id))
        ) is not None and (runner := await self.ch.get_online_runner_by_id(runner_id)) is not None:
            data["runner"] = runner.id
            if runner.in_process_job_id is not None:
                if runner.assigned_job_id is None:
                    raise Exception(
                        f"Redis data invalid: in_process_job of runner {runner_id} is set but assigned_job_id is None"
                    )
                data["progress"] = runner.assigned_job_id
        return data

    async def abort_job(self, job: JobInDb):
        jobStatus = self.job_status(job)
        assert (
            jobStatus is not JobStatus.SUCCESS or JobStatus.FAILED or JobStatus.DOWNLOADED
        ), "you cannot abort a job that has already run!"
        if jobStatus is JobStatus.NOT_QUEUED:
            job.error_msg = "Job was aborted"
        elif jobStatus is JobStatus.PENDING_RUNNER:
            await self.ch.remove_job_from_queue(job.id)
            job.error_msg = "Job was aborted"
        elif jobStatus is JobStatus.RUNNER_ASSIGNED or JobStatus.RUNNER_IN_PROGRESS:
            await self.ch.set_in_process_job(job.id, {"abort": 1})

    async def retrieve_job(self, runner_id: int) -> InProcessJob | None:
        """
        For a given online runner, retrieves the job that it has been assigned.
        Additionally, if the runner wasn't marked as processing the job yet, it
        marks it as such. If the runner has not been assigned a job, it returns
        None and does nothing.
        """
        if not (online_runner := await self.ch.get_online_runner_by_id(runner_id)):
            return None
        if online_runner.assigned_job_id is None:
            return None
        if online_runner.in_process_job_id is None:
            await self.ch.set_online_runner(
                runner_id, {"in_process_job": online_runner.assigned_job_id}
            )
        return await self.ch.get_in_process_job(online_runner.assigned_job_id)

    async def submit_job_result(
        self, online_runner: OnlineRunner, result: str, error: bool
    ) -> str | None:
        """
        Handles the submission of a job result by a runner. If the runner is not currently
        processing a job, returns an error message. Otherwise, marks the job as completed/failed
        by setting either the transcript or the error_msg field of the job, marks the runner as
        available and returns None.
        """
        if online_runner.in_process_job_id is None:
            return "Runner is not processing a job!"

        if error:
            await dp.db.finish_failed_job(online_runner, result)
        else:
            await dp.db.finish_successful_job(online_runner, result)

        await self.ch.finish_job_of_online_runner(online_runner)

        # If there are any jobs in the queue, assign one to this runner.
        # TODO: Maybe encapsulate this in a method?
        if (await self.ch.number_of_enqueued_jobs()) > 0:
            job_id = await self.ch.pop_job_with_highest_priority()
            if job_id is None:
                raise Exception("Redis data error: job queue is not empty but popmax returns None")
            await self.ch.assign_job_to_online_runner(job_id)

        logger.info(f"Marked runner {online_runner.id} as available!")
        return None

    async def enqueue_job(self, job_id: int):
        if not (await self.ch.assign_job_to_online_runner(job_id)):
            await self.ch.enqueue_new_job(job_id, 0)
            logger.info(f"No runner available for job {job_id}, enqueuing...")

    async def heartbeat(self, runner_id: int, req: HeartbeatRequest) -> HeartbeatResponse:
        # TODO: actually handle the request data for job updates and such.
        online_runner = await self.ch.get_online_runner_by_id(runner_id)
        if not online_runner:
            return HeartbeatResponse(error="This runner is not currently registered as online!")
        await self.ch.reset_runner_expiration(runner_id)
        if online_runner.in_process_job_id is not None:
            in_process_job = await self.ch.get_in_process_job(online_runner.in_process_job_id)
            if in_process_job is None:
                raise Exception(
                    "Redis data invalid: OnlineRunner has in_process_job set but the jobs key doesn't exist"
                )
            if in_process_job.abort:
                return HeartbeatResponse(abort=True)
            await self.ch.set_in_process_job(
                online_runner.in_process_job_id, {"progress": req.progress}
            )
        if online_runner.assigned_job_id:
            return HeartbeatResponse(job_assigned=True)
        return HeartbeatResponse()
