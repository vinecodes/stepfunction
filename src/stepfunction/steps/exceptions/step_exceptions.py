"""Exceptions for built-in step types.

Author: Vineeth Penugonda
"""


class StepTimeoutError(Exception):
    """Raised when a step exceeds its allowed execution time."""

    def __init__(self, timeout: float):
        super().__init__(f"Step exceeded the timeout of {timeout}s")
