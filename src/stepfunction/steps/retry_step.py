"""RetryStep — a built-in step that retries a callable on failure.

Author: Vineeth Penugonda
"""

from asyncio import sleep
from inspect import iscoroutinefunction
from typing import Any, Callable, Dict, Optional, Union

from stepfunction.constants.enums import StepType
from stepfunction.steps.base import BaseStep, FuncRef, build_callable
from stepfunction.utils.logger import setup_logger


class RetryStep(BaseStep):
    """A step that retries a callable on failure with a fixed delay between attempts.

    Executes the wrapped function and retries up to ``max_retries`` times if it
    raises an exception. Raises the last exception if all attempts fail.

    Args:
        func (Callable | BaseStep): The function to execute. May be sync or
            async, or another step (e.g. a TimeoutStep: a time limit per attempt).
        max_retries (int): Maximum number of retry attempts after the first failure.
            A value of 3 means the function is called at most 4 times. Defaults to 3.
        delay (float): Seconds to wait between retry attempts. Defaults to 1.0.

    Raises:
        ValueError: If max_retries is negative or delay is negative.

    Example:
        sf.add_step("fetch", RetryStep(func=call_api, max_retries=3, delay=2.0), next_step="next")

    Spec: ``{"type": "retry", "max_retries": 3, "delay": 2.0, "func": "call_api"}``.
    """

    step_type: StepType = StepType.INBUILT
    spec_type = "retry"

    def __init__(
        self,
        func: Union[Callable[[Any], Any], BaseStep],
        max_retries: int = 3,
        delay: float = 1.0,
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if delay < 0:
            raise ValueError("delay must be a non-negative number")

        self.func = func
        self.max_retries = max_retries
        self.delay = delay
        self.__logger = setup_logger(__name__)

    def build(self) -> Callable[[Any], Any]:
        """Return an async function that retries ``func`` on failure."""
        func = build_callable(self.func)
        max_retries = self.max_retries
        delay = self.delay

        async def run(input_value: Any) -> Any:
            self.__logger.debug(
                f"RetryStep - executing with max_retries={max_retries}, delay={delay}s"
            )
            last_exc: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    if iscoroutinefunction(func):
                        return await func(input_value)
                    return func(input_value)
                except Exception as exc:
                    last_exc = exc
                    self.__logger.warning(
                        f"RetryStep - attempt {attempt + 1}/{max_retries + 1} failed: {exc}"
                    )
                    if attempt < max_retries:
                        self.__logger.debug(f"RetryStep - retrying in {delay}s")
                        await sleep(delay)

            self.__logger.error(f"RetryStep - all {max_retries + 1} attempts exhausted")
            raise last_exc

        return run

    def to_spec(self, encode_func: Callable[[Any], FuncRef]) -> Dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "delay": self.delay,
            "func": encode_func(self.func),
        }

    @classmethod
    def from_spec(
        cls, spec: Dict[str, Any], decode_func: Callable[[FuncRef], Any]
    ) -> "RetryStep":
        return cls(
            func=decode_func(spec["func"]),
            max_retries=spec.get("max_retries", 3),
            delay=spec.get("delay", 1.0),
        )
