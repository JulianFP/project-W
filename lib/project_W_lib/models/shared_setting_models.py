from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, FilePath, NewPath


class LoggingEnum(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class BaseLoggingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: LoggingEnum = Field(
        default=LoggingEnum.INFO,
        description="What kind of log messages should be printed to the console. All messages with lower severity than this will not be logged. Possible values in order of severity: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'. Warning: The 'DEBUG' level will result in a large amount of logs that will include sensitive information like tokens and user data, as well as in a slight performance decrease. For production systems only use it temporarily to triage a bug, and remove the logs afterwards.",
        validate_default=True,
    )
    fmt: str = Field(
        default="%(name)s | [%(asctime)s %(levelname)s] %(message)s",
        description="The format of the log messages. Attributes have to be inserted in classic printf style. See https://docs.python.org/3/library/logging.html#logrecord-attributes for a list of all supported attribute names. This option is ignored if 'json_fmt' is set to true.",
        validate_default=True,
    )
    datefmt: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="How dates should be formatted inside each log message. See https://docs.python.org/3/library/time.html#time.strftime for a usage guide. This option is ignored if 'json_fmt' is set to true.",
        validate_default=True,
    )
    json_fmt: bool = Field(
        default=False,
        description="Whether all log values should be outputted as a single-line json object. The format of date/time information will also be set to ISO formatting. Great for parsing into logging systems like Grafana Loki, less good for human readability. If this option is set to true, the 'fmt' and 'datefmt' options will be ignored."
    )

class FileLoggingSettings(BaseLoggingSettings):
    model_config = ConfigDict(extra="forbid")
    path: FilePath | NewPath | None = Field(
        default=None,
        description="Path to the file where all logs should be appended to (in addition to printing them into the console). If the file doesn't exists yet, it will be created. The files directory must exist though. If unset, file logging is disabled.",
        validate_default=True,
    )

class LoggingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    console: BaseLoggingSettings = Field(
        default=BaseLoggingSettings(),
        description="Logging settings affecting the log messages printed to the console",
        validate_default=True,
    )
    file: FileLoggingSettings = Field(
        default=FileLoggingSettings(),
        description="Logging settings affecting the log messages printed to a log file",
        validate_default=True,
    )

class BaseSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    logging: LoggingSettings = Field(
        default=LoggingSettings(),
        description="Settings regarding log messages",
        validate_default=True,
    )
