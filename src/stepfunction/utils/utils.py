"""This module contains utility functions for the stepfunction package."""

from os import getenv
from typing import Optional


def get_environment_variable(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Returns the value of the environment variable with the given name.

    Args:
        name (str): The name of the environment variable.
        default (str): The default value to return if the environment variable is not set.

    Returns:
        str: The value of the environment variable.
    """
    return getenv(name, default)
