from pathlib import Path

import click
from granian.constants import HTTPModes, Interfaces
from granian.log import LogLevels
from granian.server import Server

import project_W.dependencies as dp

from ._version import __version__
from .config import load_config
from .logger import get_logger


@click.command()
@click.version_option(__version__)
@click.option(
    "--custom_config_path",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        allow_dash=False,
        path_type=Path,
    ),
    required=False,
    help="Path to search for the config.yml file in addition to the users and sites config paths (xdg dirs on Linux) and the current working directory.",
)
@click.option(
    "--development",
    is_flag=True,
    help="Start in development mode. This will reload the webserver on file change, disable https enforcement and some other changes. Never use in production!",
)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--worker_count", default=4, show_default=True)
@click.option(
    "--root_static_files",
    type=click.Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        allow_dash=False,
        path_type=Path,
    ),
    required=False,
    help="Directory with static files that should be served as the root files of this webserver. Use this option to serve the client/frontend application to the users.",
)
@click.option(
    "--ssl_certificate",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
    required=False,
    help="SSL certificate file",
)
@click.option(
    "--ssl_keyfile",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
    help="SSL key file",
)
@click.option("--ssl_keyfile_password", type=str, help="SSL key password")
def main(
    custom_config_path: Path | None,
    development: bool,
    host: str,
    port: int,
    worker_count: int,
    root_static_files: Path | None,
    ssl_certificate: Path | None,
    ssl_keyfile: Path | None,
    ssl_keyfile_password: str | None,
):
    logger = get_logger("project-W")

    # post application version for debug purposes and bug reports
    logger.info(f"Running application version {__version__}")

    dp.client_path = root_static_files

    # check ssl options
    if (not ssl_certificate and ssl_keyfile) and (ssl_certificate or ssl_keyfile):
        raise Exception(
            "Either both 'ssl_certificate' and 'ssl_keyfile' have to be set or neither."
        )
    if ssl_keyfile_password and not ssl_keyfile:
        raise Exception("If 'ssl_keyfile_password' requires 'ssl_keyfile'")

    # parse config file
    dp.config = load_config([custom_config_path]) if custom_config_path else load_config()

    if development:
        Server(
            "project_W.app",
            interface=Interfaces.ASGI,
            address=host,
            port=port,
            workers=worker_count,
            websockets=False,
            ssl_cert=ssl_certificate,
            ssl_key=ssl_keyfile,
            ssl_key_password=ssl_keyfile_password,
            respawn_failed_workers=True,
            log_level=LogLevels.debug,
            log_access=True,
            reload=True,
        ).serve()
    else:
        Server(
            "project_W.app",
            interface=Interfaces.ASGI,
            address=host,
            port=port,
            workers=worker_count,
            http=HTTPModes.http2,
            websockets=False,
            ssl_cert=ssl_certificate,
            ssl_key=ssl_keyfile,
            ssl_key_password=ssl_keyfile_password,
            respawn_failed_workers=True,
        ).serve()
