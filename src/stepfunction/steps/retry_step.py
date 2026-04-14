"""RetryStep — a built-in step that retries a callable on failure.

Author: Vineeth Penugonda
"""

from asyncio import sleep
from inspect import iscoroutinefunction
from typing import Any, Callable, Optional

from stepfunction.constants.enums import StepType
from stepfunction.steps.base import BaseStep


class RetryStep(BaseStep):
    """A step that retries a callable on failure with a fixed delay between attempts.

    Executes the wrapped function and retries up to ``max_retries`` times if it
    raises an exception. Raises the last exception if all attempts fail.

    Args:
        func (Callable): The function to execute. May be sync or async.
        max_retries (int): Maximum number of retry attempts after the first failure.
            A value of 3 means the function is called at most 4 times. Defaults to 3.
        delay (float): Seconds to wait between retry attempts. Defaults to 1.0.

    Raises:
        ValueError: If max_retries is negative or delay is negative.

    Example:
        sf.add_step("fetch", RetryStep(func=call_api, max_retries=3, delay=2.0), next_step="next")
    """

    step_type: StepType = StepType.INBUILT

    def __init__(
        self, func: Callable[[Any], Any], max_retries: int = 3, delay: float = 1.0
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if delay < 0:
            raise ValueError("delay must be a non-negative number")

        self.func = func
        self.max_retries = max_retries
        self.delay = delay

    def build(self) -> Callable[[Any], Any]:
        """Return an async function that retries ``func`` on failure."""
        func = self.func
        max_retries = self.max_retries
        delay = self.delay

        async def run(input_value: Any) -> Any:
            last_exc: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    if iscoroutinefunction(func):
                        return await func(input_value)
                    return func(input_value)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        await sleep(delay)

            raise last_exc

        return run
