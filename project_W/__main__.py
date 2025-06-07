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
def main(
    custom_config_path: Path | None,
    development: bool,
    root_static_files: Path | None,
):
    logger = get_logger("project-W")

    # post application version for debug purposes and bug reports
    logger.info(f"Running application version {__version__}")

    dp.client_path = root_static_files

    # parse config file
    dp.config = load_config([custom_config_path]) if custom_config_path else load_config()

    granian_options = {
        "target": "project_W.app",
        "interface": Interfaces.ASGI,
        "process_name": "Project-W_backend",
        "websockets": False,
        "respawn_failed_workers": True,
        "address": str(dp.config.web_server.address.ip),
        "port": dp.config.web_server.port,
        "workers": dp.config.web_server.worker_count,
    }

    if dp.config.web_server.ssl:
        granian_options["http"] = HTTPModes.http2
        granian_options["ssl_cert"] = dp.config.web_server.ssl.cert_file.absolute()
        granian_options["ssl_key"] = dp.config.web_server.ssl.key_file.absolute()
        if dp.config.web_server.ssl.key_file_password:
            granian_options["ssl_key_password"] = (
                dp.config.web_server.ssl.key_file_password.get_secret_value()
            )
    elif not dp.config.web_server.no_https:
        raise Exception(
            "You have currently no ssl settings set. This is unsupported in production since it will lead to sensitive data, keys and passwords to be transmitted unencrypted. If you still want to disable https (e.g. for testing/development purposes) then confirm this by setting 'no_https' to true"
        )

    if development:
        granian_options["log_level"] = LogLevels.debug
        granian_options["log_access"] = True
        granian_options["reload"] = True
        granian_options["reload_paths"] = [Path(__file__).parent.absolute()]
        print(granian_options["reload_paths"])

    Server(**granian_options).serve()


if __name__ == "__main__":
    main()
