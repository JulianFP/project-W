import yaml 
import logging
from pathlib import Path
from typing import Dict
import flask
from project_W.logger import get_logger

logger = get_logger("project_W")

# define default config options 
# default options will be overwritten later if they are defined in config.yml or env vars
defaultConfig = {
    "URL": "http://localhost:5000",
    "DB_PATH": ".",
    "JWT_SECRET_KEY": None,
    "SMTP_SERVER": {
        "domain": None,
        "port": 587,
        "secure": "starttls",
        "sender_email": None,
        "password": None,
    }
}

def loadConfig(app):
    #first set our app.config to the default values defined above
    app.config.update(defaultConfig)

    #next overwrite default values with values defined in config file
    # search for config file
    paths = [
        Path("/etc/project-W/config.yml"),
        Path.home().joinpath(".config", "project-W", "config.yml"),
        Path("config.yml")
    ]
    for path in paths:
        if path.exists():
            app.config.from_file(str(path), load=yaml.safe_load)
            logger.info("loaded config from " + str(path))
            break
        else: logger.info(str(path) + " doesn't exist, couldn't load config file from there")

    #finally do the same thing for env variables (this means env vars have highest precedence)
    #we only load env variables with prefix "PROJECT-W". This prefix will be removed when storing var in app.config
    fileConfig: Dict = app.config.copy()
    app.config.from_prefixed_env(prefix="PROJECT_W", loads=yaml.safe_load)
    #the following makes sure that dicts inside our dict get updated and not overwritten. dicts inside dicts in our config are not supported
    for name, value in fileConfig.items():
        if isinstance(value, Dict): value.update(app.config[name])
    app.config = fileConfig
