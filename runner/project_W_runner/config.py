from pathlib import Path

from platformdirs import site_config_path, user_config_path
from pyaml_env import parse_config
from pydantic import ValidationError

from .logger import get_logger
from .models.settings import Settings

program_name = "project-W-runner"
logger = get_logger(program_name)


class FindConfigFileException(Exception):
    pass


def find_config_file(additional_paths: list[Path] = []) -> Path:
    default_search_dirs = [
        user_config_path(appname=program_name),
        site_config_path(appname=program_name),
        Path(__file__).parent,
        Path.cwd(),
    ]
    search_dirs = additional_paths + default_search_dirs

    for dir in search_dirs:
        config_dir = dir / "config.yml"
        if config_dir.is_file():
            logger.info(f"Trying to load config from path '{str(config_dir)}'...")
            return config_dir
    raise FindConfigFileException(
        "Couldn't find a config.yml file in any search directory. Please add one"
    )


def load_config(additional_paths: list[Path] = []) -> Settings:
    config_path = find_config_file(additional_paths)
    config = parse_config(config_path)

    try:
        parsed_config = Settings(**config)
    except ValidationError as e:
        logger.critical(
            f"The following errors occurred during validation of the config file '{str(config_path)}'. Please adjust your config file according to the documentation and try again"
        )
        grouped_errors = {}
        for error in e.errors():
            grouped_errors.setdefault(error["type"], []).append(error)
        for error_type, errors in grouped_errors.items():
            print(
                f"Error '{error_type}: {errors[0]['msg']}' encountered for the following options in your config file:"
            )
            for error in errors:
                print(error["loc"])
        raise e

    logger.info(f"Successfully loaded config from path '{str(config_path)}'")
    return parsed_config
