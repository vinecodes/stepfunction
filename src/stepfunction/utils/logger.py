""" Module for setting up loggers. """

import logging
import logging.config

from stepfunction.utils.constants import (DEFAULT_LOG_LEVEL,
                                          DEFAULT_LOGGING_FORMAT,
                                          ENVIRONMENT_VARIABLE_LOG_LEVEL)
from stepfunction.utils.utils import get_environment_variable


def setup_logger(name: str | None = None, log_format: str = DEFAULT_LOGGING_FORMAT) -> logging.Logger:
    """
    Set up and return a logger with the given name.
    If no name is provided, return the root logger.
    """

    LOG_LEVEL = get_environment_variable(
        ENVIRONMENT_VARIABLE_LOG_LEVEL, DEFAULT_LOG_LEVEL)

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": log_format,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {
            "level": LOG_LEVEL,
            "handlers": ["console"],
        },
        "loggers": {
            "filecentral": {
                "level": LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },

            "botocore": {
                "level": "WARNING",  # Set level to WARNING to ignore DEBUG logs
                "handlers": ["console"],
                "propagate": False,
            },
            "urllib3.connectionpool": {
                "level": "ERROR",  # Only log errors and above to reduce noise
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)

    return logging.getLogger(name)
