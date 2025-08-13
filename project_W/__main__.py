import platform
from pathlib import Path

import click
from granian.constants import Interfaces
from granian.log import LogLevels
from granian.server import Server
from itsdangerous import URLSafeTimedSerializer

import project_W.dependencies as dp
from project_W.models.settings import SecretKeyValidated

from ._version import __commit_id__, __version__
from .config import load_config
from .logger import get_logger
from .cli_tasks import (
    execute_background_tasks,
    perform_database_encrypted_content_deletion,
    perform_secret_key_rotation,
)


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
    "--run_periodic_tasks",
    is_flag=True,
    help="Instead of starting the Project-W backend this will instead perform required periodic background tasks like database cleanups and the like. Execute this at least once a day using for example a cronjob or systemd timers!",
)
@click.option(
    "--rotate_secret_key",
    type=str,
    required=False,
    help="Instead of starting the Project-W backend this will instead re-encrypt all encrypted contents of the database with the newly provided encryption key. The old existing encryption key is read from the config file. After this operation you can change the key in the config file to the new one.",
)
@click.option(
    "--delete_encrypted_contents_from_database",
    is_flag=True,
    help="Instead of starting the Project-W backend this will instead delete all encrypted contents from the database, i.e. jobs, transcripts, and OIDC refresh tokens. Perform if you lost your encryption key,",
)
@click.option(
    "--development",
    is_flag=True,
    help="Start in development mode. This will reload the webserver on file change, disable https enforcement and some other changes. Never use in production! (Doesn't do anything if --run_periodic_tasks was set)",
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
    help="Directory with static files that should be served as the root files of this webserver. Use this option to serve the client/frontend application to the users. (Doesn't do anything if --run_periodic_tasks was set)",
)
def main(
    custom_config_path: Path | None,
    run_periodic_tasks: bool,
    rotate_secret_key: str | None,
    delete_encrypted_contents_from_database: bool,
    development: bool,
    root_static_files: Path | None,
):
    logger = get_logger("project-W")

    # post application version for debug purposes and bug reports
    logger.info(f"Running application version {__version__}")
    if __commit_id__ is None:
        raise Exception(
            "Couldn't read git hash from _version.py file. Make sure to install this package from a working git repository!"
        )
    dp.git_hash = __commit_id__.removeprefix("g")
    logger.info(f"Application was built from git hash {dp.git_hash}")
    logger.info(f"Python version: {platform.python_version()}")

    dp.client_path = root_static_files

    # parse config file
    dp.config = load_config([custom_config_path]) if custom_config_path else load_config()
    dp.auth_s = URLSafeTimedSerializer(
        dp.config.security.secret_key.root.get_secret_value(), "Project-W"
    )

    if run_periodic_tasks:
        execute_background_tasks()
        return

    if rotate_secret_key is not None:
        rotate_secret_key_validated = SecretKeyValidated.model_validate(rotate_secret_key)
        if click.confirm(
            "Are you sure that you want to re-encrypt all contents of the database? After this you will only be able to properly use the database with the new key you just provided!"
        ):
            perform_secret_key_rotation(rotate_secret_key_validated)
        return

    if delete_encrypted_contents_from_database:
        if click.confirm(
            "Are you sure that you want to delete all jobs, audio files, transcripts and OIDC auth tokens from the database?"
        ):
            perform_database_encrypted_content_deletion()
        return

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

    Server(**granian_options).serve()


if __name__ == "__main__":
    main()
