import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

import project_W.dependencies as dp
from project_W.caching import RedisAdapter
from project_W.database import PostgresAdapter
from project_W.logger import get_logger

from ._version import __version__
from .config import loadConfig
from .models.response_data import AboutResponse
from .routers import admins, users
from .security import ldap, local_account, oidc


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
        dp.config = loadConfig(additionalPaths=[path])
    else:
        dp.config = loadConfig()

    # include security routers depending on which authentication backends are configured in config file
    if dp.config.security.oidc_providers is not {}:
        app.include_router(oidc.router)
        await oidc.register_with_oidc_providers(dp.config)
    if dp.config.security.ldap_providers is not {}:
        app.include_router(ldap.router)
        ldap.ldap_adapter = ldap.LdapAdapter()
        await ldap.ldap_adapter.open(dp.config.security.ldap_providers)
    if not dp.config.security.local_account.disable:
        app.include_router(local_account.router)

    # connect to database
    dp.db = PostgresAdapter(dp.config.postgres_connection_string)
    await dp.db.open()

    # connect to caching server
    dp.ch = RedisAdapter()
    await dp.ch.open(unix_socket_path="/run/redis-project-W/redis.sock")

    await dp.db.ensure_local_user_exists("julian@partanengroup.de", "Password-1234", False, True)

    yield

    # close database connections before application exit
    await dp.db.close()


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


@app.get("/about")
async def about() -> AboutResponse:
    return AboutResponse(
        description="A self-hostable platform on which users can create transcripts of their audio files (speech-to-text) using Whisper AI",
        source_code="https://github.com/JulianFP/project-W",
        version=__version__,
    )
