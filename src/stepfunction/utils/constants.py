"""Constants for the project."""

# Logging
LIBRARY_LOGGER_NAME = "stepfunction"
"""str: The logger every module of the library logs under."""

DEFAULT_LOG_LEVEL = "INFO"
"""str: Unused since 0.2.1 (the application sets levels); kept for imports."""

DEFAULT_LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
"""str: The default logging format for the project."""

# Environment variables
ENVIRONMENT_VARIABLE_LOG_LEVEL = "LOG_LEVEL"
""" str: The environment variable for the logging level."""
