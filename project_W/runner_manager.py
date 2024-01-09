import enum
import time
from types import NoneType
from typing import Dict, Optional
from attr import dataclass
from flask import Request, jsonify
from project_W.logger import get_logger

from project_W.model import Job, Runner

logger = get_logger("project-W")

# Runners should send a heartbeat to the server
# every 5 seconds, and if they don't send a heartbeat
# for 15 seconds they may be automatically unregistered.
# TODO: Should we make these configurable?
DEFAULT_HEARTBEAT_INTERVAL = 5
DEFAULT_HEARTBEAT_TIMEOUT = 15


class JobStatus(enum.StrEnum):
    """
    Represents all the possible statuses that a
    job request might have.
    """
    # The job request has been received by the server,
    # but is not currently queued for processing.
    # TODO: Do we even need to support this?
    NOT_QUEUED = "not_queued"
    # The backend has received the job request but no
    # runner has been assigned yet
    PENDING_RUNNER = "pending_runner"
    # A runner has been assigned, but has not started processing
    # the request
    RUNNER_ASSIGNED = "runner_assigned"
    # A runner has been assigned, and is currently processing
    # the request
    RUNNER_IN_PROGRESS = "runner_in_progress"
    # The runner successfully completed the job and
    # the transcript is ready for retrieval
    SUCCESS = "success"
    # There was an error during the processing of the request
    FAILED = "failed"


@dataclass
class InProcessJob:
    """
    Represents a job that is currently being processed by a runner.
    Instances of this are created as soon as the runner retrieves the
    audio file from the server, and live until the server fully retrieves
    the completed transcript or until the runner fails.
    """
    runner: Runner
    job: Job


@dataclass
class OnlineRunner:
    """
    Represents one instance of a runner that's currently registered as online. Note
    that this is separate from the Runner class that represents a runner database entry.
    Since job assignments and such don't persist across server restarts, we don't need to
    store them to the DB anyways.
    """
    # The runner that this instance corresponds to.
    runner: Runner

    # The job that this runner is currently assigned to.
    current_job: Optional[InProcessJob]

    # Each time a runner sends a heartbeat, the result of `time.monotonic()` gets
    # stored in this timestamp. This way, we can automatically unregister runners
    # that have not sent a heartbeat in `DEFAULT_HEARTBEAT_TIMEOUT` seconds.
    last_heartbeat_timestamp: float


@dataclass
class HeartbeatResponse:
    error: Optional[str] = None
    job_assigned: Optional[bool] = None

    def jsonify(self):
        if self.error is not None:
            return jsonify(error=self.error), 400
        if self.job_assigned:
            return jsonify(job_assigned=True), 200
        return jsonify(ack=True), 200


class RunnerManager:
    """
    This class represents the runner manager and job scheduler of the server.
    It keeps track of which runners are currently registered as online, processes
    runner heartbeats, schedules and dispatches jobs to their runners and retrieves
    the job results.
    """

    # Keeps track of all runners currently registered as online, with their
    # runner IDs as keys.
    online_runners: Dict[int, OnlineRunner]
    # Keep track of all jobs that have already been assigned to a runner,
    # with their job IDs as keys.
    assigned_jobs: Dict[int, OnlineRunner]
    # A queue to keep track of all jobs that have not yet been assigned
    # to a runner. We use a python dict with None values for this, as it
    # keeps track of insertion order while also allowing for efficient
    # lookup/removal of jobs.
    job_queue: Dict[int, NoneType]
    # We also keep track of the completed transcripts for each
    transcripts: Dict[int, str]

    def __init__(self):
        self.online_runners = {}
        self.assigned_jobs = {}
        self.job_queue = {}

        # TODO: Start a background thread to periodically unregister
        # runners that haven't been responding.

    def is_runner_online(self, runner: Runner) -> bool:
        """
        Returns whether the given runner is currently registered as online.
        """
        return runner.id in self.online_runners

    def register_runner(self, runner: Runner) -> bool:
        """
        Registers the given runner as online. Returns False if the
        runner is already registered as online or True otherwise.
        Starting from the registration, the runner must periodically send
        heartbeat requests to the manager, or it may be unregistered.
        """
        if self.is_runner_online(runner):
            logger.info(f"Runner {runner.id} was already online!")
            return False
        # TODO: Do we need to use a Mutex/RWLock to mutate the runner map?
        # Python dicts are threadsafe, but it should still be considered
        # if there can be any weird race conditions.
        self.online_runners[runner.id] = OnlineRunner(
            runner=runner,
            current_job_id=None,
            last_heartbeat_timestamp=time.monotonic()
        )
        logger.info(f"Runner {runner.id} just came online!")
        return True

    def unregister_runner(self, online_runner: OnlineRunner):
        """
        Unregisters an online runner.
        """
        del self.online_runners[online_runner.runner.id]
        logger.info(f"Runner {online_runner.runner.id} just went offline!")

        # FIXME: Remove linear scan.
        if online_runner.current_job is not None \
                or online_runner in self.assigned_jobs.values():
            logger.info(f"  -> Runner was unregistered while still processing a job! Enqueuing job again.")
            self.enqueue_job(online_runner.current_job.job)

    def job_status(self, job: Job) -> JobStatus:
        if job.transcript is not None:
            return JobStatus.SUCCESS
        if job.error_msg is not None:
            return JobStatus.FAILED
        if job.id in self.job_queue:
            return JobStatus.PENDING_RUNNER
        if job.id in self.assigned_jobs:
            runner = self.assigned_jobs[job.id]
            if runner.current_job is not None:
                return JobStatus.RUNNER_IN_PROGRESS
            return JobStatus.RUNNER_ASSIGNED
        # TODO: Do we need additional logic here?
        return JobStatus.NOT_QUEUED

    def heartbeat(self, runner: Runner | None, req: Request):
        # TODO: actually handle the request data for job updates and such.
        if runner is None:
            return HeartbeatResponse(error="No runner with that token exists!")
        if not self.is_runner_online(runner):
            return HeartbeatResponse(error="This runner is not currently registered as online!")
        online_runner = self.online_runners[runner.id]
        online_runner.last_heartbeat_timestamp = time.monotonic()
        if runner.id in self.assigned_jobs:
            return HeartbeatResponse(job_assigned=True)
        return HeartbeatResponse()

    def find_available_runner(self, job: Job) -> Optional[OnlineRunner]:
        """
        Finds an appropriatre available runner for the given job.
        If no runner is available, returns None.
        """
        # TODO: We might want a runner tag system so that some runners
        # can be reserved for certain jobs.
        # TODO: Implement some kind of priority queue, so that more powerful
        # runners are preferred over weaker ones.
        for runner in self.online_runners.values():
            if runner.current_job is None:
                return runner
        return None

    def assign_job_to_runner(self, job: Job, runner: OnlineRunner):
        assert runner.current_job is None, "Runner already has an assigned job!"
        self.assigned_jobs[job.id] = runner
        logger.info(f"Assigned job {job.id} to runner {runner.runner.id}!")

    def enqueue_job(self, job: Job):
        if job.id in self.job_queue:
            return False
        if (runner := self.find_available_runner(job)) is not None:
            self.assign_job_to_runner(job, runner)
            return
        # Append the job to the end of the queue by inserting
        # it into the job_queue dict with a dummy value.
        self.job_queue[job.id] = None
        logger.info(f"No runner available for job {job.id}, enqueuing...")
