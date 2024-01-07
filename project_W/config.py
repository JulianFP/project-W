from pathlib import Path
from typing import Dict
from jsonschema import Draft202012Validator, ValidationError, validators
from platformdirs import user_data_dir, user_config_path, site_config_path
from pyaml_env import parse_config
from project_W.logger import get_logger

programName = "project-W"
logger = get_logger(programName)

def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
            validator, properties, instance, schema,
        ):
            yield error

    return validators.extend(
        validator_class, {"properties" : set_defaults},
    )

DefaultValidatingValidator = extend_with_default(Draft202012Validator)

#schema for config variables. Will be used for both the config file and env vars
schema = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "pattern": r"^(http|https):\/\/(([a-z0-9\-]+\.)+[a-z0-9\-]+|localhost)(:[0-9]+)?$",
        },
        "databasePath": {
            "type": "string",
            "default": user_data_dir(appname=programName, ensure_exists=True)
        },
        "loginSecurity": {
            "type": "object",
            "properties": {
                "sessionSecretKey": {
                    "type": [ "string", "null" ],
                    "default": None
                },
                "sessionExpirationTimeMinutes": {
                    "type": "integer",
                    "minimum": 5,
                    "default": 60
                },
                "allowedEmailDomains": {
                    "type": [ "array" ],
                    "items": {
                        "type": "string",
                        "pattern": r"^([a-z0-9\-]+\.)+[a-z0-9\-]+$"
                    },
                    "default": []
                },
                "disableSignup": {
                    "type": "boolean",
                    "default": False
                }
            },
            "additionalProperties": False,
            "default": {} #required for defaults inside object to get applied
        },
        "smtpServer": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "pattern": r"^([a-z0-9\-]+\.)+[a-z0-9\-]+|localhost$",
                },
                "port": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 65535
                },
                "secure": {
                    "type": "string",
                    "pattern": r"^ssl|starttls|unencrypted$"
                },
                "senderEmail": {
                    "type": "string"
                },
                "username": {
                    "type": "string"
                },
                "password": {
                    "type": "string"
                }
            },
            "required": [ "domain", "port", "secure", "senderEmail", "username", "password" ],
            "additionalProperties": False
        },
        "disableOptionValidation": {
            "type": "boolean",
            "default": False
        }
    },
    "required": [ "url", "smtpServer" ],
    "additionalProperties": False
}

def findConfigFile() -> Path:
    searchDirs = [ 
        user_config_path(appname=programName),
        site_config_path(appname=programName),
        Path(__file__).parent,
        Path.cwd()
    ]
    for dir in searchDirs:
        configDir = dir / "config.yml"
        if configDir.is_file(): return configDir
    raise Exception("couldn't find a config.yml file in any search directory. Please add one")

def loadConfig() -> Dict:
    configPath = findConfigFile()
    config = parse_config(configPath)

    #print warning about option if it is set
    if config.get("disableOptionValidation"):
        logger.warning("'disableOptionValidation' has been enabled in your config. Only do this for development or testing purposes, never in production!")

    #catch exception for validation with jsonscheme to implement disableOptionValidation
    #and for better exception messages in terminal and log messages
    try:
        DefaultValidatingValidator(schema).validate(config)
    except ValidationError as exc:
        if not config.get("disableOptionValidation"):
            msg = ""
            if exc.validator == "required":
                msg = "A required option is missing from your config.yml file:\n" + exc.message + "\nPlease make sure to define this option. Maybe you made a typo?"
            elif exc.validator == "additionalProperties":
                msg = "An undefined option has been found in your config.yml file:\n" + exc.message + "\nPlease remove this option from your config. Maybe you made a typo?"
            else:
                msg = "The option '" + exc.json_path + "' in your config.yml file has has an invalid value:\n" + exc.message + "\nPlease adjust this value. Maybe you made a typo?"
            logger.exception(msg)
            raise Exception(msg)
        else:
            logger.warning("Your config is invalid, some parts of this program will not work properly! Set 'disableOptionValidation' to false to learn more")

    logger.info("successfully loaded config from: " + str(configPath))
    return config
