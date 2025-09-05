import asyncio
import os
import platform
from pathlib import Path

import click

from ._version import __commit_id__, __version__
from .config import load_config
from .logger import get_logger
from .runner import Runner

logger = get_logger("project-W-runner")


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
    "--dummy",
    is_flag=True,
    help="Start in dummy mode. This will not load whisperx and not do any transcription but instead just simulate a transcription returning the same transcript every time. Only use for testing/development purposes, never in production!",
)
def main(custom_config_path: Path | None, dummy: bool):
    logger.info(f"Running application version {__version__}")
    if __commit_id__ is None:
        raise Exception(
            "Couldn't read git hash from _version.py file. Make sure to install this package from a working git repository!"
        )
    git_hash = __commit_id__.removeprefix("g")
    logger.info(f"Application was built from git hash {git_hash}")
    logger.info(f"Python version: {platform.python_version()}")

    config = load_config([custom_config_path]) if custom_config_path else load_config()

    # set env vars first before importing Runner and prefetch code because that would trigger the code that reads the env var
    os.environ["PYANNOTE_CACHE"] = str(config.whisper_settings.model_cache_dir)
    os.environ["HF_HOME"] = str(config.whisper_settings.model_cache_dir)

    if dummy:
        logger.warning(
            "Started runner in dummy mode. This runner will only simulate a transcription returning the same transcript every time. Only use for testing/development purposes, never in production!"
        )
        logger.info("Trying to import dummy transcribe code now...")
        from .utils_dummy import transcribe

        logger.info("Import successful")

    else:
        logger.info("Trying to import WhisperX code now...")
        from .utils_whisperx import prefetch_models_as_configured, transcribe

        logger.info("Import successful")

        prefetch_models_as_configured(config.whisper_settings)

    runner = Runner(
        transcribe_function=transcribe,
        config=config,
        git_hash=git_hash,
    )
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
