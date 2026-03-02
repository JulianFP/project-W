import logging.config
import json
from typing import Any
from datetime import datetime
from .models.shared_setting_models import LoggingSettings

class JsonFormatter(logging.Formatter):
    RESERVED_ATTRS = {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "taskName",
            "asctime"
        }

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).astimezone().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include all custom attributes
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and key not in log_entry:
                log_entry[key] = value

        # Include exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)

#httpx INFO logs contain sensitive information and should only be logged on DEBUG level!
def httpx_downgrade_filter(record: logging.LogRecord):
    if record.name.startswith("httpx") and record.levelno == logging.INFO:
        record.levelno = logging.DEBUG
        record.levelname = "DEBUG"
    return True

def configure_logging(logging_settings: LoggingSettings) -> dict[str, Any]:
    #configure handlers
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json_formatter" if logging_settings.console.json_fmt else "console_formatter",
            "level": logging_settings.console.level.value,
        },
    }
    if logging_settings.file.path is not None:
        handlers["file"] = {
            "class": "logging.FileHandler",
            "formatter": "json_formatter" if logging_settings.file.json_fmt else "file_formatter",
            "level": logging_settings.file.level.value,
            "filename": str(logging_settings.file.path.resolve()),
            "encoding": "utf-8",
        }

    #set logging dict
    logging_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console_formatter": {
                "format": logging_settings.console.fmt,
                "datefmt": logging_settings.console.datefmt,
            },
            "file_formatter": {
                "format": logging_settings.file.fmt,
                "datefmt": logging_settings.file.datefmt,
            },
            "json_formatter": {
                "()": JsonFormatter,
            }
        },
        "handlers": handlers,
        "root": {
            "handlers": list(handlers.keys()),
            "level": logging.DEBUG,
        },
    }

    #apply logging dict to baseConfig
    logging.config.dictConfig(logging_dict)

    #in case httpx is used, apply its filter
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.addFilter(httpx_downgrade_filter)

    #return so that application can manually apply the config somewhere else as well
    return logging_dict
