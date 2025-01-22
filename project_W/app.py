import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI

import project_W.dependencies as dp
from project_W.caching import RedisAdapter
from project_W.database import PostgresAdapter
from project_W.logger import get_logger

from ._version import __version__
from .config import loadConfig
from .model import AboutResponse, AuthRequestForm, Token
from .routers import admins, users
from .security import authenticate_user


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
    dp.db = PostgresAdapter(dp.config.postgres_connection_string)
    await dp.db.open()

    # connect to caching server
    dp.ch = RedisAdapter()
    await dp.ch.open(unix_socket_path="/run/redis-project-W/redis.sock")

    yield

    # close database connections before application exit
    await dp.db.close()


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(admins.router)


@app.post("/auth")
async def login(form_data: Annotated[AuthRequestForm, Depends()]) -> Token:
    return await authenticate_user(form_data)


@app.get("/about")
async def about() -> AboutResponse:
    return AboutResponse(
        description="A self-hostable platform on which users can create transcripts of their audio files (speech-to-text) using Whisper AI",
        source_code="https://github.com/JulianFP/project-W",
        version=__version__,
    )
