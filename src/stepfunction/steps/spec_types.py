"""Step types declarative specs can name — "timeout", "retry", "wait" and any
custom BaseStep subclass registered here.

Author: Vineeth Penugonda
"""

from typing import Dict, Type

from stepfunction.exceptions.step_errors import UnknownStepTypeError
from stepfunction.steps.base import BaseStep

_step_types: Dict[str, Type[BaseStep]] = {}


def register_step_type(cls: Type[BaseStep]) -> Type[BaseStep]:
    """Let specs name ``cls`` by its ``spec_type``.  Usable as a decorator.

    Raises:
        ValueError: If ``cls`` has no ``spec_type``, or another class is
            already registered under it.
    """
    name = getattr(cls, "spec_type", None)
    if not name:
        raise ValueError(f"{cls.__name__} has no spec_type to register it under")
    if _step_types.get(name, cls) is not cls:
        raise ValueError(
            f"Step type '{name}' is already registered by {_step_types[name].__name__}"
        )
    _step_types[name] = cls
    return cls


def step_type_class(name: str) -> Type[BaseStep]:
    """The class registered under ``name``.

    Raises:
        UnknownStepTypeError: If no class is registered under it.
    """
    try:
        return _step_types[name]
    except KeyError:
        raise UnknownStepTypeError(name) from None
