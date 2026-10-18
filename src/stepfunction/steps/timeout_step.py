"""TimeoutStep — a built-in step that enforces a maximum execution duration.

Author: Vineeth Penugonda
"""

from asyncio import TimeoutError as AsyncTimeoutError
from asyncio import get_running_loop, wait_for
from inspect import iscoroutinefunction
from typing import Any, Callable, Dict, Union

from stepfunction.constants.enums import StepType
from stepfunction.steps.base import BaseStep, FuncRef, build_callable
from stepfunction.steps.exceptions import StepTimeoutError
from stepfunction.utils.logger import setup_logger


class TimeoutStep(BaseStep):
    """A step that raises an error if the wrapped callable exceeds a time limit.

    Works with both sync and async functions. Sync functions are executed in a
    thread pool so the timeout can be enforced without blocking the event loop.

    Args:
        func (Callable | BaseStep): The function to execute. May be sync or
            async, or another step (e.g. a RetryStep: a time limit on all
            its attempts together).
        timeout (float): Maximum allowed duration in seconds.

    Raises:
        ValueError: If timeout is not a positive number.
        StepTimeoutError: If the function does not complete within ``timeout`` seconds.

    Example:
        sf.add_step("process", TimeoutStep(func=heavy_job, timeout=30.0), next_step="next")

    Spec: ``{"type": "timeout", "timeout": 30.0, "func": "heavy_job"}``.
    """

    step_type: StepType = StepType.INBUILT
    spec_type = "timeout"

    def __init__(self, func: Union[Callable[[Any], Any], BaseStep], timeout: float):
        if timeout <= 0:
            raise ValueError("timeout must be a positive number")

        self.func = func
        self.timeout = timeout
        self.__logger = setup_logger(__name__)

    def build(self) -> Callable[[Any], Any]:
        """Return an async function that enforces a timeout on ``func``."""
        func = build_callable(self.func)
        timeout = self.timeout

        async def run(input_value: Any) -> Any:
            self.__logger.debug(f"TimeoutStep - executing with timeout of {timeout}s")
            try:
                if iscoroutinefunction(func):
                    return await wait_for(func(input_value), timeout=timeout)
                else:
                    loop = get_running_loop()
                    return await wait_for(
                        loop.run_in_executor(None, func, input_value),
                        timeout=timeout,
                    )
            except AsyncTimeoutError:
                self.__logger.error(f"TimeoutStep - exceeded timeout of {timeout}s")
                raise StepTimeoutError(timeout)

        return run

    def to_spec(self, encode_func: Callable[[Any], FuncRef]) -> Dict[str, Any]:
        return {"timeout": self.timeout, "func": encode_func(self.func)}

    @classmethod
    def from_spec(
        cls, spec: Dict[str, Any], decode_func: Callable[[FuncRef], Any]
    ) -> "TimeoutStep":
        return cls(func=decode_func(spec["func"]), timeout=spec["timeout"])
