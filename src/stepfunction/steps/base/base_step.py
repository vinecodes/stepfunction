"""Base class for building custom step types.

Author: Vineeth Penugonda
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Union

from stepfunction.constants.enums import StepType

# A wrapped function as a spec holds it: a registered name, or a nested step's spec
FuncRef = Union[str, Dict[str, Any]]


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
        spec_type (Optional[str]): The name declarative specs (``to_dict`` /
            ``from_dict``) use for this step type, e.g. ``"timeout"``. ``None``
            (the default) means the step can't be exported. To make a custom
            step exportable, set it, implement ``to_spec`` and ``from_spec``,
            and register the class with
            ``stepfunction.steps.register_step_type()``.

    Methods:
        build(): Return the callable that the StepFunction will execute.
        to_spec(): This step's settings as JSON-able values.
        from_spec(): Rebuild a step from those settings.

    Example:
        class MultiplyStep(BaseStep):
            spec_type = "multiply"

            def __init__(self, factor: float):
                self.factor = factor

            def build(self) -> Callable:
                async def run(input_value: Any) -> Any:
                    return input_value * self.factor
                return run

            def to_spec(self, encode_func):
                return {"factor": self.factor}

            @classmethod
            def from_spec(cls, spec, decode_func):
                return cls(factor=spec["factor"])

        register_step_type(MultiplyStep)
        sf.add_step("double", MultiplyStep(factor=2), next_step="next")
    """

    step_type: StepType = StepType.EXTERNAL
    spec_type: Optional[str] = None

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

    def to_spec(self, encode_func: Callable[[Any], FuncRef]) -> Dict[str, Any]:
        """This step's settings as JSON-able values (without ``"type"``, which
        the serializer adds from ``spec_type``).

        Args:
            encode_func: Turns a function this step wraps (a registered
                callable or another ``BaseStep``) into its reference in the
                spec. Use it for every callable setting.
        """
        raise NotImplementedError(f"{type(self).__name__} doesn't implement to_spec()")

    @classmethod
    def from_spec(
        cls, spec: Dict[str, Any], decode_func: Callable[[FuncRef], Any]
    ) -> "BaseStep":
        """Rebuild a step from the settings ``to_spec`` produced.

        Args:
            spec: The settings, ``"type"`` included.
            decode_func: Turns a function reference back into the callable
                (or ``BaseStep``) it names.
        """
        raise NotImplementedError(f"{cls.__name__} doesn't implement from_spec()")


def build_callable(func: Union[Callable[[Any], Any], BaseStep]) -> Callable[[Any], Any]:
    """``func`` itself, or what a wrapped step builds."""
    return func.build() if isinstance(func, BaseStep) else func
