import enum
import threading
import time
from typing import Dict, Optional, Tuple
from attr import dataclass
from flask import Request, jsonify, Flask
from project_W.utils import AddressablePriorityQueue, auth_token_from_req, synchronized
from project_W.logger import get_logger

from project_W.model import Job, Runner, get_runner_by_token, db

logger = get_logger("project-W")

# Runners should send a heartbeat to the server
# every 15 seconds, and if they don't send a heartbeat
# for 60 seconds they may be automatically unregistered.
# TODO: Should we make these configurable?
DEFAULT_HEARTBEAT_INTERVAL = 15
DEFAULT_HEARTBEAT_TIMEOUT = 60


class JobStatus(enum.Enum):
    """
    Represents all the possible statuses that a
    job request might have.
    """
    # The job request has been received by the server,
    # but is not currently queued for processing.
    # TODO: Do we even need to support this?
    NOT_QUEUED = "notQueued"
    # The backend has received the job request but no
    # runner has been assigned yet
    PENDING_RUNNER = "pendingRunner"
    # A runner has been assigned, but has not started processing
    # the request
    RUNNER_ASSIGNED = "runnerAssigned"
    # A runner has been assigned, and is currently processing
    # the request
    RUNNER_IN_PROGRESS = "runnerInProgress"
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
    job_id: int
    # A float between 0 and 1 representing the progress of the job.
    progress: float = 0.0

    def job(self) -> Job:
        return db.session.query(Job).where(self.job_id == Job.id).one_or_none()


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

    # The id of the job that was assigned to the runner, if any.
    # If this is not None, but `in_process_job` is None,
    # then the runner has been assigned a job but has not
    # yet started processing it.
    assigned_job_id: Optional[int]
    # The job that this runner is currently processing.
    in_process_job: Optional[InProcessJob]

    # Each time a runner sends a heartbeat, the result of `time.monotonic()` gets
    # stored in this timestamp. This way, we can automatically unregister runners
    # that have not sent a heartbeat in `DEFAULT_HEARTBEAT_TIMEOUT` seconds.
    last_heartbeat_timestamp: float

    def assigned_job(self) -> Optional[Job]:
        if self.assigned_job_id is None:
            return None
        return db.session.query(Job).where(self.assigned_job_id == Job.id).one_or_none()


@dataclass
class HeartbeatResponse:
    error: Optional[str] = None
    job_assigned: Optional[bool] = None

    def jsonify(self):
        if self.error is not None:
            return jsonify(error=self.error), 400
        if self.job_assigned:
            return jsonify(jobAssigned=True), 200
        return jsonify(ack=True), 200


class RunnerManager:
    """
    This class represents the runner manager and job scheduler of the server.
    It keeps track of which runners are currently registered as online, processes
    runner heartbeats, schedules and dispatches jobs to their runners and retrieves
    the job results.
    """

    # We need this because the cleanup thread needs to be able to access
    # the app context.
    app: Flask
    # Keeps track of all runners currently registered as online, with their
    # runner IDs as keys.
    online_runners: Dict[int, OnlineRunner]
    # Keep track of all jobs that have already been assigned to a runner,
    # with their job IDs as keys.
    assigned_jobs: Dict[int, OnlineRunner]
    # A queue to keep track of all jobs that have not yet been assigned
    # to a runner. The keys are the job IDs, and the values are the
    # job priorities (right now they're all 0).
    # TODO: Actually add job priorities.
    job_queue: AddressablePriorityQueue[int, int]

    # We use this mutex to ensure that there are no race conditions
    # between the background thread and the any API calls. Note that
    # because the background thread runs very infrequently, the lock
    # contention should be quite low most of the time. Any method that
    # accesses or mutates the runner manager state should be decorated
    # with `@synchronized("mtx")`.
    mtx: threading.RLock

    def background_thread(self):
        logger.info("Starting background thread")
        while True:
            self.cleanup_pass()
            time.sleep(10)

    @synchronized("mtx")
    def cleanup_pass(self):
        """
        This method checks for any online runners that have not sent a heartbeat
        in `DEFAULT_HEARTBEAT_TIMEOUT` seconds, and unregisters them, as they likely
        had some sort of outage. This method is called periodically (but infrequently)
        by the background thread.
        """
        with self.app.app_context():
            now = time.monotonic()
            runners_to_unregister = []
            for online_runner in self.online_runners.values():
                time_since_last_heartbeat = now - online_runner.last_heartbeat_timestamp
                if time_since_last_heartbeat > DEFAULT_HEARTBEAT_TIMEOUT:
                    logger.info(
                        f"Runner {online_runner.runner.id} hasn't sent a heartbeat in {time_since_last_heartbeat:.2f} seconds, unregistering...")
                    runners_to_unregister.append(online_runner)

            for online_runner in runners_to_unregister:
                self.unregister_runner(online_runner)

    def __init__(self, app: Flask):
        self.app = app
        self.mtx = threading.RLock()
        self.online_runners = {}
        self.assigned_jobs = {}
        self.job_queue = AddressablePriorityQueue()
        threading.Thread(target=self.background_thread,
                         name="runner_manager_bg", daemon=True).start()

    def load_jobs_from_db(self):
        """
        Enqueues all jobs from the database that are not currently queued.
        Currently, this is only called once just after the server startup
        """
        for job in db.session.query(Job):
            if self.job_status(job) == JobStatus.NOT_QUEUED:
                self.enqueue_job(job)

    @synchronized("mtx")
    def is_runner_online(self, runner: Runner) -> bool:
        """
        Returns whether the given runner is currently registered as online.
        """
        return runner.id in self.online_runners

    @synchronized("mtx")
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
        self.online_runners[runner.id] = OnlineRunner(
            runner=runner,
            last_heartbeat_timestamp=time.monotonic(),
            assigned_job_id=None,
            in_process_job=None,
        )
        logger.info(f"Runner {runner.id} just came online!")

        # TODO: If we have runner tags, only assign job if it has the right tag.
        if len(self.job_queue) > 0:
            job_id, _ = self.job_queue.pop_max()
            job = db.session.query(Job).where(job_id == Job.id).one_or_none()
            self.assign_job_to_runner(job, self.online_runners[runner.id])

        return True

    @synchronized("mtx")
    def unregister_runner(self, online_runner: OnlineRunner) -> bool:
        """
        Unregisters an online runner.
        """
        if online_runner.runner.id not in self.online_runners:
            logger.info(f"Runner {online_runner.runner.id} was not online!")
            return False
        del self.online_runners[online_runner.runner.id]
        logger.info(f"Runner {online_runner.runner.id} just went offline!")

        if online_runner.assigned_job_id is not None:
            logger.info(
                f"  -> Runner was unregistered while still processing a job! Enqueuing job again.")
            self.enqueue_job(online_runner.assigned_job())
        return True

    @synchronized("mtx")
    def get_online_runner_for_req(self, request: Request) -> Tuple[OnlineRunner, None] | Tuple[None, str]:
        """
        Returns the online runner whose token is specified in the Authorization header of
        the request. If the token doesn't correspond to any online runner, returns
        `(None, error_message)`.
        """
        token, error = auth_token_from_req(request)
        if error is not None:
            return None, error
        runner = get_runner_by_token(token)
        if runner is None:
            return None, "No runner with that token exists!"
        if not self.is_runner_online(runner):
            return None, "This runner is not currently registered as online!"
        return self.online_runners[runner.id], None

    @synchronized("mtx")
    def job_status(self, job: Job) -> JobStatus:
        if job.transcript is not None:
            return JobStatus.SUCCESS
        if job.error_msg is not None:
            return JobStatus.FAILED
        if job.id in self.job_queue:
            return JobStatus.PENDING_RUNNER
        if (runner := self.assigned_jobs.get(job.id)) is not None:
            if runner.in_process_job is not None:
                return JobStatus.RUNNER_IN_PROGRESS
            return JobStatus.RUNNER_ASSIGNED
        # TODO: Do we need additional logic here?
        return JobStatus.NOT_QUEUED

    def status_dict(self, job: Job) -> dict:
        data = {"step": self.job_status(job).value}
        if (runner := self.assigned_jobs.get(job.id)) is not None:
            data["runner"] = runner.runner.id
            if runner.in_process_job is not None:
                data["progress"] = runner.in_process_job.progress
        return data

    @synchronized("mtx")
    def find_available_runner(self, job: Job) -> Optional[OnlineRunner]:
        """
        Finds an appropriate available runner for the given job.
        If no runner is available, returns None.
        """
        # TODO: We might want a runner tag system so that some runners
        # can be reserved for certain jobs.
        # TODO: Implement some kind of priority queue, so that more powerful
        # runners are preferred over weaker ones.
        for runner in self.online_runners.values():
            if runner.in_process_job is None:
                return runner
        return None

    @synchronized("mtx")
    def assign_job_to_runner(self, job: Job, runner: OnlineRunner):
        assert runner.assigned_job_id is None and runner.in_process_job is None, \
            "Runner already has an assigned job!"
        self.assigned_jobs[job.id] = runner
        runner.assigned_job_id = job.id
        logger.info(f"Assigned job {job.id} to runner {runner.runner.id}!")

    @synchronized("mtx")
    def retrieve_job(self, online_runner: OnlineRunner) -> Optional[Job]:
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
                runner=online_runner.runner,
                job_id=online_runner.assigned_job_id
            )
        return online_runner.assigned_job()

    @synchronized("mtx")
    def submit_job_result(self, online_runner: OnlineRunner, result: str, error: bool) -> Optional[str]:
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
        logger.info(f"Marked runner {online_runner.runner.id} as available!")
        return None

    @synchronized("mtx")
    def enqueue_job(self, job: Job):
        if job.id in self.job_queue:
            return False
        if (runner := self.find_available_runner(job)) is not None:
            self.assign_job_to_runner(job, runner)
            return
        # Append the job to the end of the queue by inserting
        # it into the job_queue dict with a dummy value.
        # TODO: Insert using job priority once added.
        self.job_queue.push(job.id, 0)
        logger.info(f"No runner available for job {job.id}, enqueuing...")

    @synchronized("mtx")
    def heartbeat(self, runner: Runner | None, req: Request) -> HeartbeatResponse:
        # TODO: actually handle the request data for job updates and such.
        if runner is None:
            return HeartbeatResponse(error="No runner with that token exists!")
        if not self.is_runner_online(runner):
            return HeartbeatResponse(error="This runner is not currently registered as online!")
        online_runner = self.online_runners[runner.id]
        online_runner.last_heartbeat_timestamp = time.monotonic()
        if online_runner.assigned_job_id:
            return HeartbeatResponse(job_assigned=True)
        if online_runner.in_process_job is not None \
                and (progress := req.args.get("progress", type=float)) is not None:
            job = online_runner.in_process_job
            job.progress = progress
        return HeartbeatResponse()
