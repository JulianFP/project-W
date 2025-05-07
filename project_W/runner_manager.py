import time
from typing import Optional, Tuple, Union

from project_W.logger import get_logger

from .caching import CachingAdapter
from .models.internal import JobStatus, OnlineRunner, RunnerInDb

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

    def load_jobs_from_db(self):
        """
        Enqueues all jobs from the database that are not finished yet.
        We do not need to check if it already is in the queue since enqueue_job
        already does that (-> no mutex needed for this method)
        Currently, this is only called once just after the server startup
        """
        for job in db.session.query(Job):
            if self.job_status(job) not in [
                JobStatus.SUCCESS,
                JobStatus.FAILED,
                JobStatus.DOWNLOADED,
            ]:
                self.enqueue_job(job)

    async def is_runner_online(self, runner_id: int) -> bool:
        """
        Returns whether the given runner is currently registered as online.
        """
        return (await self.ch.get_online_runner_by_id(runner_id)) is not None

    async def register_runner(self, runner: RunnerInDb) -> bool:
        """
        Registers the given runner as online. Returns False if the
        runner is already registered as online or True otherwise.
        Starting from the registration, the runner must periodically send
        heartbeat requests to the manager, or it may be unregistered.
        """
        if self.is_runner_online(runner.id):
            logger.info(f"Runner {runner.id} was already online!")
            return False
        await self.ch.register_new_online_runner(
            OnlineRunner(
                runner_id=runner.id, runner_priority=100, last_heartbeat_timestamp=time.monotonic()
            )
        )  # TODO: priority
        logger.info(f"Runner {runner.id} just came online!")

        # TODO: If we have runner tags, only assign job if it has the right tag.
        if len(self.job_queue) > 0:
            job_id, _ = self.job_queue.pop_max()
            job = db.session.query(Job).where(job_id == Job.id).one_or_none()
            await self.assign_job_to_runner(job, self.online_runners[runner.id])

        return True

    async def unregister_runner(self, online_runner: OnlineRunner) -> bool:
        """
        Unregisters an online runner.
        """
        if not await self.is_runner_online(online_runner.runner_id):
            logger.info(f"Runner {online_runner.runner_id} was not online!")
            return False
        await self.ch.unregister_online_runner(online_runner.runner_id)
        logger.info(f"Runner {online_runner.runner_id} just went offline!")

        if online_runner.assigned_job_id is not None:
            logger.info(
                f"  -> Runner was unregistered while still processing a job! Enqueuing job again."
            )
            await self.enqueue_job(online_runner.assigned_job_id)
        return True

    async def job_status(self, job: Job) -> JobStatus:
        if job.downloaded:
            return JobStatus.DOWNLOADED
        if job.transcript is not None:
            return JobStatus.SUCCESS
        if job.error_msg is not None:
            return JobStatus.FAILED
        if job.id in self.job_queue:
            return JobStatus.PENDING_RUNNER
        if (
            runner_id := (await self.ch.get_online_runner_by_assigned_job(job.id))
        ) is not None and (runner := await self.ch.get_online_runner_by_id(runner_id)) is not None:
            if runner.in_process_job is not None:
                return JobStatus.RUNNER_IN_PROGRESS
            return JobStatus.RUNNER_ASSIGNED
        # TODO: Do we need additional logic here?
        return JobStatus.NOT_QUEUED

    async def status_dict(self, job: Job) -> dict:
        data = {"step": self.job_status(job).value}
        if (runner := self.assigned_jobs.get(job.id)) is not None:
            data["runner"] = runner.runner.id
            if runner.in_process_job is not None:
                data["progress"] = runner.in_process_job.progress
        return data

    async def find_available_runner(self, job: Job) -> Optional[OnlineRunner]:
        """
        Finds an appropriate available runner for the given job.
        If no runner is available, returns None.
        """
        # TODO: We might want a runner tag system so that some runners
        # can be reserved for certain jobs.
        # TODO: Implement some kind of priority queue, so that more powerful
        # runners are preferred over weaker ones.
        for runner in self.online_runners.values():
            if runner.assigned_job_id is None:
                return runner
        return None

    async def assign_job_to_runner(self, job: Job, runner: OnlineRunner):
        assert (
            runner.assigned_job_id is None and runner.in_process_job is None
        ), "Runner already has an assigned job!"
        self.assigned_jobs[job.id] = runner
        runner.assigned_job_id = job.id
        logger.info(f"Assigned job {job.id} to runner {runner.runner.id}!")

    async def abort_job(self, job: Job):
        jobStatus = self.job_status(job)
        assert (
            jobStatus is not JobStatus.SUCCESS or JobStatus.FAILED or JobStatus.DOWNLOADED
        ), "you cannot abort a job that has already run!"
        if jobStatus is JobStatus.NOT_QUEUED:
            job.set_error("job was aborted")
        elif jobStatus is JobStatus.PENDING_RUNNER:
            del self.job_queue[job.id]
            job.set_error("job was aborted")
        elif jobStatus is JobStatus.RUNNER_ASSIGNED or JobStatus.RUNNER_IN_PROGRESS:
            online_runner = self.assigned_jobs[job.id]
            online_runner.in_process_job.abort = True

    async def retrieve_job(self, online_runner: OnlineRunner) -> Optional[Job]:
        """
        For a given online runner, retrieves the job that it has been assigned.
        Additionally, if the runner wasn't marked as processing the job yet, it
        marks it as such. If the runner has not been assigned a job, it returns
        None and does nothing.
        """
        if online_runner.assigned_job_id is None:
            return None
        if online_runner.in_process_job is None:
            online_runner.in_process_job = InProcessJob(
                runner=online_runner.runner, job_id=online_runner.assigned_job_id
            )
        return online_runner.assigned_job()

    async def submit_job_result(
        self, online_runner: OnlineRunner, result: str, error: bool
    ) -> Optional[str]:
        """
        Handles the submission of a job result by a runner. If the runner is not currently
        processing a job, returns an error message. Otherwise, marks the job as completed/failed
        by setting either the transcript or the error_msg field of the job, marks the runner as
        available and returns None.
        """
        if online_runner.in_process_job is None:
            return "Runner is not processing a job!"
        job = online_runner.in_process_job.job()
        if error:
            job.set_error(result)
        else:
            job.set_transcript(result)
        del self.assigned_jobs[job.id]
        online_runner.in_process_job = None
        online_runner.assigned_job_id = None

        # If there are any jobs in the queue, assign one to this runner.
        # TODO: Maybe encapsulate this in a method?
        if len(self.job_queue) > 0:
            job_id, _ = self.job_queue.pop_max()
            job = db.session.query(Job).where(job_id == Job.id).one_or_none()
            self.assign_job_to_runner(job, online_runner)

        logger.info(f"Marked runner {online_runner.runner.id} as available!")
        return None

    async def enqueue_job(self, job: Job):
        if job.id in self.job_queue:
            return False
        if (runner := self.find_available_runner(job)) is not None:
            await self.assign_job_to_runner(job, runner)
            return
        # TODO: Insert using job priority once added.
        self.job_queue.push(job.id, 0)
        logger.info(f"No runner available for job {job.id}, enqueuing...")

    async def heartbeat(self, runner: Optional[Runner], req: Request) -> HeartbeatResponse:
        # TODO: actually handle the request data for job updates and such.
        if runner is None:
            return HeartbeatResponse(error="No runner with that token exists!")
        if not self.is_runner_online(runner):
            return HeartbeatResponse(error="This runner is not currently registered as online!")
        online_runner = self.online_runners[runner.id]
        online_runner.last_heartbeat_timestamp = time.monotonic()
        if (
            online_runner.in_process_job is not None
            and (progress := req.form.get("progress", type=float)) is not None
        ):
            online_runner.in_process_job.progress = progress
            if online_runner.in_process_job.abort:
                return HeartbeatResponse(abort=True)
        if online_runner.assigned_job_id:
            return HeartbeatResponse(job_assigned=True)
        return HeartbeatResponse()
