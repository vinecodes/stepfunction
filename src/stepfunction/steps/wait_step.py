"""WaitStep — a built-in step that pauses execution for a fixed interval.

Author: Vineeth Penugonda
"""

from asyncio import sleep
from typing import Any, Callable

from stepfunction.constants.enums import StepType
from stepfunction.steps.base import BaseStep
from stepfunction.utils.logger import setup_logger


class WaitStep(BaseStep):
    """A step that pauses workflow execution for a fixed duration.

    The input value is passed through unchanged so the next step receives
    exactly what the previous step produced.

    Args:
        duration (float): Number of seconds to wait before proceeding.

    Example:
        sf.add_step("pause", WaitStep(duration=5), next_step="next_step")
    """

    step_type: StepType = StepType.INBUILT

    def __init__(self, duration: float):
        if duration < 0:
            raise ValueError("duration must be a non-negative number")
        self.duration = duration
        self.__logger = setup_logger(__name__)

    def build(self) -> Callable[[Any], Any]:
        """Return an async function that sleeps for ``duration`` seconds."""
        duration = self.duration

        async def wait(input_value: Any) -> Any:
            self.__logger.debug(f"WaitStep - sleeping for {duration}s")
            await sleep(duration)
            self.__logger.debug(f"WaitStep - resumed after {duration}s")
            return input_value

        return wait
