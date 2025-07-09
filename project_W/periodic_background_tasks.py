import asyncio

import project_W.dependencies as dp

from .database import PostgresAdapter
from .logger import get_logger
from .smtp import SmtpClient

logger = get_logger("project-W")


async def database_cleanup():
    logger.info("Starting database cleanup task...")
    dp.db = PostgresAdapter(str(dp.config.postgres_connection_string))
    await dp.db.open()
    dp.smtp = SmtpClient(dp.config.smtp_server)
    await dp.smtp.open()

    if dp.config.cleanup.user_retention_in_days is not None:
        await dp.db.user_cleanup(dp.config.cleanup.user_retention_in_days)
    if dp.config.cleanup.finished_job_retention_in_days is not None:
        await dp.db.job_cleanup(dp.config.cleanup.finished_job_retention_in_days)
    await dp.db.general_cleanup()

    await dp.db.close()
    await dp.smtp.close()
    logger.info("Finished database cleanup task")


def execute_background_tasks():
    asyncio.run(database_cleanup())
