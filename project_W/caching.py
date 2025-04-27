from abc import ABC, abstractmethod

import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff

from .logger import get_logger


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


class RedisAdapter(CachingAdapter):
    async def open(self, host="localhost", port=6379, password=None, unix_socket_path=None):
        # 3 retries on timeout
        retry = Retry(ExponentialBackoff(), 3)
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            unix_socket_path=unix_socket_path,
            retry=retry,
            retry_on_timeout=True,
        )  # implicitly creates connection pool

        if not await self.client.ping():
            raise Exception(
                "Critical: Redis doesn't answer to pings. Make sure the redis server is up and running and the connection settings are correct!"
            )

        await self.__check_server_version()

        self.logger.info("Successfully connected to Redis")

    async def __check_server_version(self):
        redis_version = (await self.client.execute_command("INFO"))["redis_version"]
        self.logger.info(f"Redis server is on version {redis_version}")

    async def close(self):
        self.logger.info("Closing Redis connections...")
        await self.client.close()
