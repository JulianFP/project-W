import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

import project_W.dependencies as dp

from ._version import __version__
from .caching import RedisAdapter
from .config import load_config
from .database import PostgresAdapter
from .logger import get_logger
from .models.response_data import AboutResponse
from .models.settings import LocalAccountOperationModeEnum
from .routers import admins, jobs, ldap, local_account, oidc, runners, users
from .security import ldap_deps, oidc_deps
from .smtp import SmtpClient


# startup database connections before spinning up application
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = get_logger("project-W")

    # post application version for debug purposes and bug reports
    logger.info(f"Running application version {__version__}")

    # parse config file
    config_file_path_from_env = os.environ.get("PROJECT-W_CONFIG-FILE")
    if config_file_path_from_env:
        path = Path(config_file_path_from_env)
        if not path.is_dir():
            path = path.parent
        dp.config = load_config(additional_paths=[path])
    else:
        dp.config = load_config()

    # connect to database
    dp.db = PostgresAdapter(str(dp.config.postgres_connection_string))
    await dp.db.open()

    # connect to caching server
    dp.ch = RedisAdapter()
    await dp.ch.open(dp.config.redis_connection)

    # connect to smtp server
    dp.smtp = SmtpClient(dp.config.smtp_server)
    await dp.smtp.open()

    # include security routers depending on which authentication backends are configured in config file
    login_method_exists = False
    if dp.config.security.oidc_providers is not {}:
        login_method_exists = True
        app.include_router(oidc.router)
        await oidc_deps.register_with_oidc_providers(dp.config)
    if dp.config.security.ldap_providers is not {}:
        login_method_exists = True
        app.include_router(ldap.router)
        ldap_deps.ldap_adapter = ldap_deps.LdapAdapter()
        await ldap_deps.ldap_adapter.open(dp.config.security.ldap_providers)
    if dp.config.security.local_account.mode != LocalAccountOperationModeEnum.DISABLED:
        login_method_exists = True
        app.include_router(local_account.router)
        for prov_num, prov_user in dp.config.security.local_account.user_provisioning.items():
            await dp.db.ensure_local_user_is_provisioned(
                prov_num, prov_user.email, prov_user.password, prov_user.is_admin
            )
    if not login_method_exists:
        raise Exception(
            "No login method (one of local_account, ldap or oidc) has been specified in the config!"
        )

    # enqueue all jobs from the database that are not finished yet
    for job_id in await dp.db.get_all_ids_of_unfinished_jobs():
        await dp.ch.enqueue_new_job(job_id, 0)

    yield

    # close connections before application exit
    await dp.db.close()
    await dp.ch.close()
    await dp.smtp.close()
    await ldap_deps.ldap_adapter.close()


# this can be in Markdown
app_description = """
## About Project-W

Project-W is a platform for creating transcripts of audio files (speech-to-text). It leverages OpenAIs Whisper models for the transcription while providing an API and easy-to-use interface for users to create and manage transcription jobs.

Refer to the [full documentation](https://project-w.readthedocs.io) for more information. You can also find the source code all of it's components on GitHub:
- [Backend](https://github.com/julianFP/project-w)
- [Frontend](https://github.com/julianFP/project-w-frontend)
- [Runner](https://github.com/julianFP/project-w-runner)

The API is split into the following sections:

### users
For regular users to manage their accounts

### admins
For admin users to manage the server and all users on it

### oidc, ldap and local_account
Different authentication (login, signup, etc.) routes for different authentication backends

### jobs
Submit new transcription jobs, manage existing ones
"""

app = FastAPI(
    title="Project-W",
    description=app_description,
    summary="Create transcripts of audio files (speech-to-text)!",
    version=__version__,
    license_info={
        "name": "GNU Affero General Public License Version 3",
        "identifier": "AGPL-3.0-only",
        "url": "https://www.gnu.org/licenses/agpl-3.0.txt",
    },
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))  # for oidc

app.include_router(users.router)
app.include_router(admins.router)
app.include_router(jobs.router)
app.include_router(runners.router)


@app.get("/about")
async def about() -> AboutResponse:
    return AboutResponse(
        description="A self-hostable platform on which users can create transcripts of their audio files (speech-to-text) using Whisper AI",
        source_code="https://github.com/JulianFP/project-W",
        version=__version__,
    )
