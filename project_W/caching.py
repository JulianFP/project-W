from abc import ABC, abstractmethod

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff

from .logger import get_logger
from .models.internal import OnlineRunner


class CachingAdapter(ABC):
    logger = get_logger("project-W")

    @abstractmethod
    async def open(self, host="localhost", port=6379, password=None, unix_socket_path=None):
        """
        This method initiates the redis connection pool and is called only on application startup.
        """
        pass

    @abstractmethod
    async def close(self):
        """
        This method teares down the redis connections and is called only on application shutdown
        """
        pass

    @abstractmethod
    async def register_new_online_runner(self, new_online_runner: OnlineRunner):
        """
        This method registers a runner as online
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
    async def assign_job_to_online_runner(self, job_id: int) -> bool:
        """
        Assign a job with job_id to an online runner
        Return True if successful
        Return False if there was no free runner available
        """
        pass

    @abstractmethod
    async def unregister_online_runner(self, runner_id: int):
        """
        Unregister an existing online runner (i.e. remove it from caching, it went offline)
        """
        pass

    @abstractmethod
    async def get_online_runner_by_assigned_job(self, job_id: int) -> int | None:
        """
        Returns the runner id of the runner that the job with the id job_id is currently assigned to
        Returns None if not found
        """
        pass


class RedisAdapter(CachingAdapter):

    __heartbeat_timeout = 5

    __runner_sorted_set_name = "online_runners_sorted"

    def __get_runner_key(self, runner_id: int) -> str:
        return f"online_runner:{str(runner_id)}"

    def __get_job_key(self, job_id: int) -> str:
        return f"assigned_job:{str(job_id)}"

    async def open(self, host="localhost", port=6379, password=None, unix_socket_path=None):
        # 3 retries on timeout
        retry = Retry(ExponentialBackoff(), 3)
        self.client = redis.StrictRedis(
            host=host,
            port=port,
            password=password,
            unix_socket_path=unix_socket_path,
            retry=retry,
            retry_on_timeout=True,
            decode_responses=True,
        )  # implicitly creates connection pool

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
            key_name = self.__get_runner_key(new_online_runner.runner_id)
            pipe.hset(key_name, mapping=new_online_runner.model_dump(exclude_none=True))
            pipe.expire(key_name, self.__heartbeat_timeout)
            pipe.zadd(
                self.__runner_sorted_set_name,
                {str(new_online_runner.runner_id): new_online_runner.runner_priority},
            )
            await pipe.execute()

    async def get_online_runner_by_id(self, runner_id: int) -> OnlineRunner | None:
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hgetall(self.__get_runner_key(runner_id))
            (runner_dict,) = await pipe.execute()
            if not runner_dict:
                return None
            return OnlineRunner.model_validate(runner_dict)

    async def assign_job_to_online_runner(self, job_id: int):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.zrevrange(self.__runner_sorted_set_name, 0, 0)
            (ids_returned,) = await pipe.execute()
            if len(ids_returned) == 0:
                return False
            else:
                runner_id = ids_returned[0]
            key_name = self.__get_runner_key(runner_id)
            pipe.hgetall(key_name)
            (runner_dict,) = await pipe.execute()
            while not runner_dict:
                pipe.zrem(self.__runner_sorted_set_name, runner_id)
                pipe.zrevrange(self.__runner_sorted_set_name, 0, 0)
                _, ids_returned = await pipe.execute()
                if len(ids_returned) == 0:
                    return False
                else:
                    runner_id = ids_returned[0]
                key_name = self.__get_runner_key(runner_id)
                pipe.hgetall(key_name)
                (runner_dict,) = await pipe.execute()

            online_runner = OnlineRunner.model_validate(runner_dict)
            if online_runner.assigned_job_id is None:
                online_runner.assigned_job_id = job_id
                pipe.hset(key_name, mapping=online_runner.model_dump(exclude_none=True))
                pipe.set(self.__get_job_key(job_id), runner_id)
                await pipe.execute()
                return True
            else:
                return False

    async def unregister_online_runner(self, runner_id: int):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.delete(self.__get_runner_key(runner_id))
            pipe.zrem("online_runners_sorted", runner_id)
            await pipe.execute()

    async def get_online_runner_by_assigned_job(self, job_id: int) -> int | None:
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.get(self.__get_job_key(job_id))
            (runner_id,) = await pipe.execute()
            return runner_id
