import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

import project_W.dependencies as dp
from project_W.database import postgres_adapter
from project_W.logger import get_logger

from ._version import __version__
from .config import loadConfig
from .model import AboutResponse
from .routers import admins, users


# startup database connections before spinning up application
@asynccontextmanager
async def lifespan(_):
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

    # connect to database
    dp.db = postgres_adapter(dp.config["postgresConnectionString"])
    await dp.db.open()

    # check jwt secret key and setup jwt_handler
    secret_key = dp.config["loginSecurity"]["sessionSecretKey"]
    if secret_key is not None and len(secret_key) > 16:
        logger.info("Setting sessionSecretKey from supplied config or env var")
    else:
        logger.warning("sessionSecretKey not set or too short: generating random secret key")
        # new secret key -> invalidates any existing tokens
        secret_key = secrets.token_urlsafe(64)
    dp.jwt_handler.setup(dp.db, secret_key)

    yield

    # close database applications before application exit
    await dp.db.close()


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(admins.router)


@app.get("/about")
async def about() -> AboutResponse:
    return AboutResponse(
        description="A self-hostable platform on which users can create transcripts of their audio files (speech-to-text) using Whisper AI",
        source_code="https://github.com/JulianFP/project-W",
        version=__version__,
    )
