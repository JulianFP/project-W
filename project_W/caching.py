from abc import ABC, abstractmethod
from typing import AsyncGenerator

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff

from .logger import get_logger
from .models.internal import InProcessJob, OnlineRunner
from .models.settings import RedisConnection


class CachingAdapter(ABC):
    logger = get_logger("project-W")

    @abstractmethod
    async def open(self, connection_obj):
        """
        This method initiates the connection pool and is called only on application startup.
        """
        pass

    @abstractmethod
    async def close(self):
        """
        This method teares down the connections and is called only on application shutdown
        """
        pass

    @abstractmethod
    async def register_new_online_runner(self, new_online_runner: OnlineRunner):
        """
        This method registers a runner as online
        """
        pass

    @abstractmethod
    async def reset_runner_expiration(self, runner_id: int):
        """
        Resets the expiration time (TTL) of the runner with runner_id to its initial value if it exists if it exists
        """
        pass

    @abstractmethod
    async def set_online_runner(
        self, runner_id: int, mapping: dict[str, bytes | str | int | float]
    ):
        """
        Set in online runner attributes
        """
        pass

    @abstractmethod
    async def get_online_runner_by_id(self, runner_id: int) -> OnlineRunner | None:
        """
        Get all attributes associated with an online runner by querying it using its id
        Return None if no online runner exists with that id
        """
        pass

    @abstractmethod
    async def assign_job_to_online_runner(self, job_id: int, user_id: int) -> bool:
        """
        Assign a job with job_id to an online runner
        Return True if successful
        Return False if there was no free runner available
        """
        pass

    @abstractmethod
    async def finish_job_of_online_runner(self, runner: OnlineRunner):
        """
        Marks that runner as free, removes the job from processing jobs and readds the runner to the runner queue
        """
        pass

    @abstractmethod
    async def unregister_online_runner(self, runner_id: int):
        """
        Unregister an existing online runner (i.e. remove it from caching, it went offline)
        """
        pass

    @abstractmethod
    async def get_online_runner_id_by_assigned_job(self, job_id: int) -> int | None:
        """
        Returns the runner id of the runner that the job with the id job_id is currently assigned to
        Returns None if not found
        """
        pass

    @abstractmethod
    async def enqueue_new_job(self, job_id: int, job_priority: int, user_id: int):
        """
        Push a new job into the job queue
        """
        pass

    @abstractmethod
    async def number_of_enqueued_jobs(self) -> int:
        """
        Returns the amount of jobs that are currently in the job queue
        """
        pass

    @abstractmethod
    async def pop_job_with_highest_priority(self) -> int | None:
        """
        Returns id of job with highest priority in queue, removes it from queue
        Returns None if there are no jobs in the queue
        """
        pass

    @abstractmethod
    async def remove_job_from_queue(self, job_id: int):
        """
        Removes the job with the id job_id from the queue if it exists, regardless its position
        """
        pass

    @abstractmethod
    async def get_in_process_job(self, job_id: int) -> InProcessJob | None:
        """
        Returns InProcessJob attributes for job_id, or None if there are no in process jobs with that id
        """
        pass

    @abstractmethod
    async def set_in_process_job(self, job_id: int, mapping: dict[str, bytes | str | int | float]):
        """
        Set in process job attributes
        """
        pass

    @abstractmethod
    async def get_job_pos_in_queue(self, job_id: int) -> int | None:
        """
        Returns the position of the job in the queue
        Returns None if the job isn't in the queue
        """
        pass

    @abstractmethod
    async def event_generator(self, user_id: int) -> AsyncGenerator[str, None]:
        """
        This is a Generator method that returns events regarding jobs
         of user with id user_id in a SSE format
        """
        yield ""


class RedisAdapter(CachingAdapter):

    __heartbeat_timeout = 60

    __runner_sorted_set_name = "online_runners_sorted"

    __job_queue_sorted_set_name = "job_queue_sorted"

    def __get_runner_key(self, runner_id: int) -> str:
        return f"online_runner:{str(runner_id)}"

    def __get_job_key(self, job_id: int) -> str:
        return f"in_process_job:{str(job_id)}"

    def __get_pubsub_channel(self, user_id: int) -> str:
        return f"job_events:{str(user_id)}"

    async def open(self, connection_obj: RedisConnection):
        # 3 retries on timeout
        retry = Retry(ExponentialBackoff(), 3)
        self.client = redis.StrictRedis(
            unix_socket_path=str(connection_obj.unix_socket_path),
            retry=retry,
            retry_on_timeout=True,
            decode_responses=True,
        )  # implicitly creates connection pool
        if connection_obj.connection_string is not None:
            self.client = self.client.from_url(str(connection_obj.connection_string))

        if not await self.client.ping():
            raise Exception(
                "Critical: Redis doesn't answer to pings. Make sure the redis server is up and running and the connection settings are correct!"
            )

        await self.__check_server_version()

        self.logger.info("Successfully connected to Redis")

    async def __check_server_version(self):
        query_result = await self.client.execute_command("INFO")
        if query_result is None:
            raise Exception("Could not check Redis server version")
        redis_version = query_result["redis_version"]
        self.logger.info(f"Redis server is on version {redis_version}")

    async def close(self):
        self.logger.info("Closing Redis connections...")
        await self.client.close()

    async def register_new_online_runner(self, new_online_runner: OnlineRunner):
        async with self.client.pipeline(transaction=True) as pipe:
            key_name = self.__get_runner_key(new_online_runner.id)
            pipe.hset(
                key_name, mapping=new_online_runner.model_dump(exclude_none=True, exclude={"id"})
            )
            pipe.expire(key_name, self.__heartbeat_timeout)
            pipe.zadd(
                self.__runner_sorted_set_name,
                {str(new_online_runner.id): new_online_runner.priority},
            )
            await pipe.execute()

    async def reset_runner_expiration(self, runner_id: int):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.expire(self.__get_runner_key(runner_id), self.__heartbeat_timeout)
            await pipe.execute()

    async def set_online_runner(
        self, runner_id: int, mapping: dict[str, bytes | str | int | float]
    ):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hset(self.__get_runner_key(runner_id), mapping=mapping)
            await pipe.execute()

    async def get_online_runner_by_id(self, runner_id: int) -> OnlineRunner | None:
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hgetall(self.__get_runner_key(runner_id))
            (runner_dict,) = await pipe.execute()
            if not runner_dict:
                return None
            return OnlineRunner.model_validate(runner_dict | {"id": runner_id})

    async def assign_job_to_online_runner(self, job_id: int, user_id: int):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.zpopmax(self.__runner_sorted_set_name)
            (ids_returned,) = await pipe.execute()
            if len(ids_returned) == 0:
                return False
            else:
                runner_id = ids_returned[0][0]
            key_name = self.__get_runner_key(runner_id)
            pipe.hgetall(key_name)
            (runner_dict,) = await pipe.execute()
            while not runner_dict:
                pipe.zpopmax(self.__runner_sorted_set_name)
                (ids_returned,) = await pipe.execute()
                if len(ids_returned) == 0:
                    return False
                else:
                    runner_id = ids_returned[0][0]
                key_name = self.__get_runner_key(runner_id)
                pipe.hgetall(key_name)
                (runner_dict,) = await pipe.execute()

            online_runner = OnlineRunner.model_validate(runner_dict | {"id": int(runner_id)})
            if online_runner.assigned_job_id is None:
                online_runner.assigned_job_id = job_id
                pipe.hset(key_name, mapping=online_runner.model_dump(exclude_none=True))
                pipe.hset(
                    self.__get_job_key(job_id),
                    mapping={
                        "runner_id": runner_id,
                        "user_id": user_id,
                        "progress": 0.0,
                        "abort": 0,
                    },
                )
                pipe.publish(self.__get_pubsub_channel(user_id), job_id)
                await pipe.execute()
                return True
            else:
                return False

    async def finish_job_of_online_runner(self, runner: OnlineRunner):
        assert runner.in_process_job_id is not None
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hget(self.__get_job_key(runner.in_process_job_id), "user_id")
            (user_id,) = await pipe.execute()
            pipe.delete(self.__get_job_key(runner.in_process_job_id))
            pipe.hdel(self.__get_runner_key(runner.id), *["in_process_job_id", "assigned_job_id"])
            pipe.zadd(
                self.__runner_sorted_set_name,
                {str(runner.id): runner.priority},
            )
            pipe.publish(self.__get_pubsub_channel(user_id), runner.in_process_job_id)
            await pipe.execute()

    async def unregister_online_runner(self, runner_id: int):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hget(self.__get_runner_key(runner_id), "assigned_job_id")
            pipe.delete(self.__get_runner_key(runner_id))
            pipe.zrem("online_runners_sorted", runner_id)
            (job_id, _, _) = await pipe.execute()
            if job_id is not None:
                pipe.hget(self.__get_job_key(job_id), "user_id")
                (user_id,) = await pipe.execute()
                pipe.delete(self.__get_job_key(job_id))
                pipe.publish(self.__get_pubsub_channel(user_id), job_id)
                await pipe.execute()

    async def get_online_runner_id_by_assigned_job(self, job_id: int) -> int | None:
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hget(self.__get_job_key(job_id), "runner_id")
            (runner_id,) = await pipe.execute()
            return int(runner_id)

    async def enqueue_new_job(self, job_id: int, job_priority: int, user_id: int):
        if not (
            await self.assign_job_to_online_runner(job_id, user_id)
        ):  # try to assign job to a free runner first
            async with self.client.pipeline(transaction=True) as pipe:
                pipe.zadd(self.__job_queue_sorted_set_name, {str(job_id): job_priority})
                await pipe.execute()

    async def number_of_enqueued_jobs(self) -> int:
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.zcard(self.__job_queue_sorted_set_name)
            (length,) = await pipe.execute()
            return length

    async def remove_job_from_queue(self, job_id: int):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.zrem(self.__job_queue_sorted_set_name, job_id)
            await pipe.execute()

    async def pop_job_with_highest_priority(self) -> int | None:
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.zpopmax(self.__job_queue_sorted_set_name)
            (ids_returned,) = await pipe.execute()
            if len(ids_returned) == 0:
                return None
            else:
                job_id = ids_returned[0][0]
                await pipe.execute()
                return int(job_id)

    async def get_in_process_job(self, job_id: int) -> InProcessJob | None:
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hgetall(self.__get_job_key(job_id))
            (job_dict,) = await pipe.execute()
            if job_dict:
                return InProcessJob.model_validate(job_dict | {"id": job_id})
            else:
                return None

    async def set_in_process_job(self, job_id: int, mapping: dict[str, bytes | str | int | float]):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hget(self.__get_job_key(job_id), "user_id")
            (user_id,) = await pipe.execute()
            pipe.hset(self.__get_job_key(job_id), mapping=mapping)
            pipe.publish(self.__get_pubsub_channel(user_id), job_id)
            await pipe.execute()

    async def get_job_pos_in_queue(self, job_id: int) -> int | None:
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.zrevrank(self.__job_queue_sorted_set_name, job_id)
            (position,) = await pipe.execute()
            return position

    async def event_generator(self, user_id: int) -> AsyncGenerator[str, None]:
        async with self.client.pubsub() as pubsub:
            await pubsub.subscribe(self.__get_pubsub_channel(user_id))
            async for message in pubsub.listen():
                data = message["data"]
                print(data)
                yield f"event: job_updated\ndata: {data}\n\n"
        print("exited")
