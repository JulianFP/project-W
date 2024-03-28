from pathlib import Path
from typing import Dict, List
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

class findConfigFileException(Exception):
    pass

class prettyValidationError(ValidationError):
    pass

#schema for config variables. Will be used for both the config file and env vars
schema = {
    "type": "object",
    "properties": {
        "clientURL": {
            "type": "string",
            "pattern": r"^(http|https):\/\/(([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost)(:[0-9]+)?((\/[a-zA-Z0-9\-]+)+)?(\/#)?$",
            "description": "URL under which the frontend is served. It is used for providing the user with clickable links inside of account-activation or password-reset emails. The URL should fullfill the following requirements:\n\n- It has to start with either 'http://' or 'https://'\n\n- It should contain the port number if it is not just 80 (default of http) or 443 (default of https)\n\n- It should contain the root path under which the frontend is served if its not just /\n- It should end with /# if the frontend uses hash based routing (which our frontend does!)",
            "examples": [
                "https://example.com/#",
                "https://sub.example.org/apps/project-W/frontend/#",
                "http://localhost:5173/#",
                "http://192.168.1.100:5173/#"
            ]
        },
        "databasePath": {
            "type": "string",
            "default": user_data_dir(appname=programName),
            "description": "Path under which the sqlite 'database.db' file will be stored. This database contains all backend data, so make sure to backup this directory. Changing this option for an existing installation without moving the file manually will result in the creation of a new empty database. The default value is the users data dir which under Linux is `$XDG_DATA_HOME/project-W` (most of the time this is `~/.local/share/project-W`)"
        },
        "loginSecurity": {
            "type": "object",
            "properties": {
                "sessionSecretKey": {
                    "type": [ "string", "null" ],
                    "default": None,
                    "description": "The secret key used to generate JWT Tokens. Make sure to keep this secret since with this key an attacker could log in as any user. A new key can be generated with the following command: `python -c 'import secrets; print(secrets.token_hex())'`. If left to 'None', then the server will generate a secret key for you, however it will not put it into your config file! This means that the secret key will be different after every server restart which will invalidate all JWT Tokens. It is recommended to generate a secret key yourself using the command above."
                },
                "sessionExpirationTimeMinutes": {
                    "type": "integer",
                    "minimum": 5,
                    "default": 60,
                    "description": "Time for which a users/clients JWT Tokens stay valid (in minutes). After this time the user will be logged out automatically and has to authenticate again using their username and password."
                },
                "allowedEmailDomains": {
                    "type": [ "array" ],
                    "items": {
                        "type": "string",
                        "pattern": r"^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+$"
                    },
                    "default": [],
                    "examples": [
                        ["uni-heidelberg.de", "stud.uni-heidelberg.de"]
                        
                    ],
                    "description": "Allowed domains in email addresses. Users will only be able to sign up/change their email if their email address uses one of these domains (the part after the '@'). If left empty, then all email domains are allowed."
                },
                "disableSignup": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether signup of new accounts should be possible. If set to 'true' then only users who already have an account will be able to use the service."
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
                    "pattern": r"^([a-zA-Z0-9\-]+\.)+[a-zA-Z0-9\-]+|localhost$",
                    "description": "FQDN of your smtp server."
                },
                "port": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 65535,
                    "description": "Port that should be used for the smtp connection."
                },
                "secure": {
                    "type": "string",
                    "pattern": r"^ssl|starttls|unencrypted$",
                    "description": "Whether to use ssl, starttls or no encryption with the smtp server."
                },
                "senderEmail": {
                    "type": "string",
                    "description": "Email address from which emails will be sent to the users."
                },
                "username": {
                    "type": "string",
                    "description": "Username that should be used to authenticate with the smtp server. Most of the time this is the same as 'senderEmail'."
                },
                "password": {
                    "type": "string",
                    "description": "Password that should be used to authenticate with the smtp server."
                }
            },
            "required": [ "domain", "port", "secure", "senderEmail", "username", "password" ],
            "additionalProperties": False
        },
        "disableOptionValidation": {
            "type": "boolean",
            "default": False,
            "description": "This disables the jsonschema validation of the provided config file. This means that the server will start and run even though it loaded possibly invalid data which may cause it to crash or not work proberly. Only set this to 'true' for development or testing purposes, never in production!"
        }
    },
    "required": [ "clientURL", "smtpServer" ],
    "additionalProperties": False
}

def findConfigFile(additionalPaths: List[Path] = []) -> Path:
    defaultSearchDirs = [ 
        user_config_path(appname=programName),
        site_config_path(appname=programName),
        Path(__file__).parent,
        Path.cwd()
    ]
    searchDirs = additionalPaths + defaultSearchDirs

    for dir in searchDirs:
        configDir = dir / "config.yml"
        if configDir.is_file(): 
            logger.info("Trying to load config from: " + str(configDir))
            return configDir
    raise findConfigFileException("couldn't find a config.yml file in any search directory. Please add one")

def loadConfig(additionalPaths: List[Path] = []) -> Dict:
    configPath = findConfigFile(additionalPaths)
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
            raise prettyValidationError(msg)
        else:
            logger.warning("Your config is invalid, some parts of this program will not work properly! Set 'disableOptionValidation' to false to learn more")

    logger.info("successfully loaded config from: " + str(configPath))
    return config
