import asyncio

import project_W.dependencies as dp
from project_W.models.settings import SecretKeyValidated

from .database import PostgresAdapter
from .logger import get_logger
from .security import ldap_deps, oidc_deps
from .smtp import SmtpClient

logger = get_logger("project-W")


async def db_init():
    dp.db = PostgresAdapter(str(dp.config.postgres_connection_string))
    await dp.db.open()


async def db_finish():
    await dp.db.close()


async def init():
    await db_init()
    dp.smtp = SmtpClient(dp.config.smtp_server)
    await dp.smtp.open()
    if dp.config.security.oidc_providers:
        await oidc_deps.register_with_oidc_providers(dp.config)
    if dp.config.security.ldap_providers:
        ldap_deps.ldap_adapter = ldap_deps.LdapAdapter()
        await ldap_deps.ldap_adapter.open(dp.config.security.ldap_providers)


async def finish():
    await db_finish()
    await dp.smtp.close()
    await ldap_deps.ldap_adapter.close()


async def database_cleanup():
    logger.info("Starting database cleanup task...")
    if dp.config.cleanup.user_retention_in_days is not None:
        await dp.db.user_cleanup(dp.config.cleanup.user_retention_in_days)
    if dp.config.cleanup.finished_job_retention_in_days is not None:
        await dp.db.job_cleanup(dp.config.cleanup.finished_job_retention_in_days)
    await dp.db.general_cleanup()
    logger.info("Finished database cleanup task")


async def oidc_token_invalidation():
    logger.info(
        "Starting cleanup of tokens associated with non-existing OIDC users or users with insufficient permissions..."
    )
    tokens_of_oidc_users = await dp.db.get_oidc_tokens()
    for token in tokens_of_oidc_users:
        await oidc_deps.invalidate_token_if_oidc_user_lost_privileges(token)
    logger.info(
        f"Finished cleanup of OIDC tokens, successfully checked {len(tokens_of_oidc_users)}"
    )


async def ldap_token_invalidation():
    logger.info(
        "Starting cleanup of tokens associated with non-existing LDAP users or users with insufficient permissions..."
    )
    tokens_of_ldap_users = await dp.db.get_ldap_tokens()
    for token in tokens_of_ldap_users:
        await ldap_deps.invalidate_token_if_ldap_user_lost_privileges(ldap_deps.ldap_adapter, token)
    logger.info(
        f"Finished cleanup of LDAP tokens, successfully checked {len(tokens_of_ldap_users)}"
    )


async def background_tasks_loop():
    await init()
    await database_cleanup()
    await oidc_token_invalidation()
    await ldap_token_invalidation()
    await finish()


async def database_secret_rotation_loop(secret_key: SecretKeyValidated):
    await db_init()
    await dp.db.rotate_secret_key(secret_key)
    await db_finish()


async def database_delete_encryption_loop():
    await db_init()
    await dp.db.delete_encrypted_content()
    await db_finish()


def execute_background_tasks():
    logger.info("Starting background tasks...")
    asyncio.run(background_tasks_loop())
    logger.info("Finished all background tasks")


def perform_secret_key_rotation(secret_key: SecretKeyValidated):
    logger.info("Starting database re-encryption...")
    asyncio.run(database_secret_rotation_loop(secret_key))
    logger.info("Finished database re-encryption")


def perform_database_encrypted_content_deletion():
    logger.info("Starting deletion of encrypted contents in database...")
    asyncio.run(database_delete_encryption_loop())
    logger.info(
        "Finished deletion of encrypted contents in database. Don't forget to also flush redis"
    )
