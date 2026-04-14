"""Base class for building custom step types.

Author: Vineeth Penugonda
"""

from abc import ABC, abstractmethod
from typing import Any, Callable

from stepfunction.constants.enums import StepType


class BaseStep(ABC):
    """Abstract base class for building reusable, configurable step types.

    Extend this class to create custom step types that encapsulate their own
    logic and configuration. Pass an instance directly to ``StepFunction.add_step()``
    — the framework will call ``build()`` automatically.

    Class Attributes:
        step_type (StepType): Marks the origin of the step.
            - ``StepType.EXTERNAL`` (default) — user-defined step.
            - ``StepType.INBUILT`` — provided by the stepfunction library.
            Override this in your subclass only if you are building library steps.

    Methods:
        build(): Return the callable that the StepFunction will execute.

    Example:
        class MultiplyStep(BaseStep):
            def __init__(self, factor: float):
                self.factor = factor

            def build(self) -> Callable:
                async def run(input_value: Any) -> Any:
                    return input_value * self.factor
                return run

        sf.add_step("double", MultiplyStep(factor=2), next_step="next")
    """

    step_type: StepType = StepType.EXTERNAL

    @abstractmethod
    def build(self) -> Callable[[Any], Any]:
        """Return the callable that this step will execute.

        The returned callable must accept a single positional argument
        (the input value passed from the previous step) and return a value
        that will be forwarded to the next step. It may be either a regular
        function or a coroutine function.

        Returns:
            Callable[[Any], Any]: The step function to execute.
        """
