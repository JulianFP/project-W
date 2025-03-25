from pathlib import Path

from platformdirs import site_config_path, user_config_path
from pyaml_env import parse_config
from pydantic import ValidationError

from project_W.logger import get_logger

from .models.settings import Settings

programName = "project-W"
logger = get_logger(programName)


class FindConfigFileException(Exception):
    pass


def find_config_file(additionalPaths: list[Path] = []) -> Path:
    defaultSearchDirs = [
        user_config_path(appname=programName),
        site_config_path(appname=programName),
        Path(__file__).parent,
        Path.cwd(),
    ]
    searchDirs = additionalPaths + defaultSearchDirs

    for dir in searchDirs:
        configDir = dir / "config.yml"
        if configDir.is_file():
            logger.info(f"Trying to load config from path '{str(configDir)}'...")
            return configDir
    raise FindConfigFileException(
        "Couldn't find a config.yml file in any search directory. Please add one"
    )


def loadConfig(additionalPaths: list[Path] = []) -> Settings:
    configPath = find_config_file(additionalPaths)
    config = parse_config(configPath)

    try:
        parsed_config = Settings(**config)
    except ValidationError as e:
        logger.critical(
            f"The following errors occurred during validation of the config file '{str(configPath)}'. Please adjust your config file according to the documentation and try again"
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

    logger.info(f"Successfully loaded config from path '{str(configPath)}'")
    return parsed_config
