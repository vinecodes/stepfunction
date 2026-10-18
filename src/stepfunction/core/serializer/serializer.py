"""Encode/decode logic for declarative (JSON-able dict) StepFunction specs.

Author: Vineeth Penugonda
"""

from typing import Any, Callable, Dict, Optional, cast

from stepfunction.core.step_function.step_function import StepFunction
from stepfunction.exceptions.step_errors import (
    UnregisteredFunctionError,
    UnserializableStepError,
)
from stepfunction.registry.step_registry import StepRegistry
from stepfunction.registry.step_registry import registry as default_registry
from stepfunction.steps import step_type_class
from stepfunction.steps.base import BaseStep, FuncRef
from stepfunction.types.step_types import StepParams


def _name_for_or_raise(
    step_registry: StepRegistry, func: Callable[[Any], Any], step_name: str
) -> str:
    name = step_registry.name_for(func)
    if name is None:
        raise UnregisteredFunctionError(
            f"The function used in step '{step_name}' is not registered in the "
            "given registry, so its name can't be determined for export. "
            "Register it with stepfunction.registry.step_registry.register_step() first."
        )
    return name


def _encode_func_ref(func: Any, step_registry: StepRegistry, step_name: str) -> FuncRef:
    """A function a step runs or wraps: its registered name, or — another
    step — that step's spec."""
    if isinstance(func, BaseStep):
        return _encode_base_step(func, step_registry, step_name)
    return _name_for_or_raise(step_registry, func, step_name)


def _encode_base_step(
    base_step: BaseStep, step_registry: StepRegistry, step_name: str
) -> Dict[str, Any]:
    """``{"type": <spec_type>, ...its settings}``."""
    if not base_step.spec_type:
        raise UnserializableStepError(step_name, type(base_step).__name__)
    settings = base_step.to_spec(
        lambda func: _encode_func_ref(func, step_registry, step_name)
    )
    return {"type": base_step.spec_type, **settings}


def _decode_func_ref(ref: FuncRef, step_registry: StepRegistry) -> Any:
    if isinstance(ref, dict):
        return _decode_base_step(ref, step_registry)
    return step_registry.get(ref)


def _decode_base_step(spec: Dict[str, Any], step_registry: StepRegistry) -> BaseStep:
    return step_type_class(spec["type"]).from_spec(
        spec, lambda ref: _decode_func_ref(ref, step_registry)
    )


def _encode_step(
    step_name: str, step: StepParams, step_registry: StepRegistry
) -> Dict[str, Any]:
    encoded: Dict[str, Any] = {
        "next_step": step["next_step"],
        "on_failure": step["on_failure"],
        "parallel": step["parallel"],
        "stop_on_failure": step["stop_on_failure"],
    }

    if step["is_sub_step_function"]:
        sub_step_function = cast(StepFunction, step["sub_step_function"])
        encoded["sub_step_function"] = encode_step_function(
            sub_step_function, step_registry
        )
        return encoded

    base_step = step.get("base_step")  # absent from a StepParams built by hand
    if step["parallel"]:
        # Each task: its registered name, or the spec of the step it was built from
        func_map = cast(Dict[str, Callable[[Any], Any]], step["func"])
        task_steps = cast(Dict[str, BaseStep], base_step or {})
        encoded["func"] = {
            slot: _encode_func_ref(task_steps.get(slot, fn), step_registry, step_name)
            for slot, fn in func_map.items()
        }
    elif isinstance(base_step, BaseStep):
        # Built from a BaseStep: the step's own settings, not the closure it built
        encoded["step"] = _encode_base_step(base_step, step_registry, step_name)
    else:
        func = cast(Callable[[Any], Any], step["func"])
        encoded["func"] = _name_for_or_raise(step_registry, func, step_name)

    if step.get("params") is not None:
        encoded["params"] = step["params"]
    if step.get("branch_params") is not None:
        encoded["branch_params"] = step["branch_params"]

    branch = step["branch"]
    if branch is not None:
        if callable(branch):
            encoded["branch"] = _name_for_or_raise(step_registry, branch, step_name)
        else:
            encoded["branch"] = dict(branch)  # string keys: add_step refuses others

    return encoded


def encode_step_function(
    sf: StepFunction, step_registry: Optional[StepRegistry] = None
) -> Dict[str, Any]:
    """Export ``sf`` as a JSON-able dict.

    Recurses into nested sub-step-functions by calling itself again, so
    arbitrary nesting depth is handled without special-casing.

    A step built from a BaseStep (TimeoutStep, RetryStep, WaitStep, or a
    registered custom step) is exported as ``"step": {"type": ..., settings}``
    in place of ``"func"``; a function it wraps is its registered name, or
    the nested step's spec.

    Raises:
        UnserializableStepError: If a step was built from a BaseStep
            subclass without a ``spec_type``.
        UnregisteredFunctionError: If a step or branch function used in
            ``sf`` has no registered name in ``step_registry``.
    """
    step_registry = step_registry or default_registry

    return {
        "name": sf.name,
        "start_step": sf.current_step,
        "steps": {
            step_name: _encode_step(step_name, step, step_registry)
            for step_name, step in sf.steps.items()
        },
    }


def decode_step_function(
    data: Dict[str, Any],
    step_registry: Optional[StepRegistry] = None,
    _validate: bool = True,
) -> StepFunction:
    """Reconstruct a StepFunction from a dict produced by ``encode_step_function``.

    Rebuilds the workflow purely through ``add_step``/``add_sub_step_function``/
    ``set_start_step`` — the same public API a user would call by hand — and
    recurses into nested "sub_step_function" entries by calling itself again.
    Validates exactly once, at the very end, at the outermost level only:
    ``StepFunction.validate()`` already recurses into sub-step functions and
    reports a readable breadcrumb across nesting levels, so a malformed
    nested spec still fails fast without the decoder needing its own
    recursive validation pass.

    Raises:
        UnregisteredFunctionError: If a referenced function name isn't
            registered in ``step_registry`` (defaults to the package's
            default singleton registry if not given).
        UnknownStepTypeError: If a ``"step"`` names a type no class is
            registered for.
        ValueError: If the reconstructed workflow fails validate().
    """
    step_registry = step_registry or default_registry

    sf = StepFunction(data["name"])

    for step_name, step_data in data["steps"].items():
        if "sub_step_function" in step_data:
            sub_step_function = decode_step_function(
                step_data["sub_step_function"], step_registry, _validate=False
            )
            sf.add_sub_step_function(
                step_name,
                sub_step_function=sub_step_function,
                next_step=step_data.get("next_step"),
                on_failure=step_data.get("on_failure"),
            )
            continue

        if "step" in step_data:
            func: Any = _decode_base_step(step_data["step"], step_registry)
        elif isinstance(step_data["func"], dict):
            func = {
                slot: _decode_func_ref(ref, step_registry)
                for slot, ref in step_data["func"].items()
            }
        else:
            func = step_registry.get(step_data["func"])

        branch_spec = step_data.get("branch")
        if branch_spec is None:
            branch: Any = None
        elif isinstance(branch_spec, dict):
            branch = dict(branch_spec)
        else:
            branch = step_registry.get(branch_spec)

        sf.add_step(
            step_name,
            func,
            next_step=step_data.get("next_step"),
            on_failure=step_data.get("on_failure"),
            branch=branch,
            parallel=step_data.get("parallel", False),
            stop_on_failure=step_data.get("stop_on_failure", False),
            params=step_data.get("params"),
            branch_params=step_data.get("branch_params"),
        )

    start_step = data.get("start_step")
    if start_step is not None:
        sf.set_start_step(start_step)

    if _validate:
        sf.validate()

    return sf
