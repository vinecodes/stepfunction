"""Module for setting up loggers.

The library logs under the ``stepfunction`` logger and never configures
logging for the application: it adds no handlers to the root logger and
changes no other logger. The application decides where logs go (e.g.
``logging.basicConfig(level=logging.INFO)``). Without any configuration,
Python prints warnings and errors to stderr.

``LOG_LEVEL``, if set in the environment, sets the level of the
``stepfunction`` logger only.
"""

import logging
from typing import Optional

from stepfunction.utils.constants import (
    DEFAULT_LOGGING_FORMAT,
    ENVIRONMENT_VARIABLE_LOG_LEVEL,
    LIBRARY_LOGGER_NAME,
)
from stepfunction.utils.utils import get_environment_variable


def _configure_library_logger() -> logging.Logger:
    """Give the library's logger a NullHandler (once) and the LOG_LEVEL, if set."""
    library = logging.getLogger(LIBRARY_LOGGER_NAME)

    if not any(isinstance(h, logging.NullHandler) for h in library.handlers):
        library.addHandler(logging.NullHandler())

    level = get_environment_variable(ENVIRONMENT_VARIABLE_LOG_LEVEL)
    if level:
        library.setLevel(level.upper())

    return library


def setup_logger(
    name: Optional[str] = None, log_format: str = DEFAULT_LOGGING_FORMAT
) -> logging.Logger:
    """
    Return the logger with the given name (the library's ``stepfunction``
    logger if no name is given).

    ``log_format`` is accepted for backwards compatibility and ignored:
    formatting belongs to the application's logging configuration.
    """
    _configure_library_logger()

    return logging.getLogger(name or LIBRARY_LOGGER_NAME)
