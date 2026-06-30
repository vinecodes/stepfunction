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


def _encode_step(
    step_name: str, step: StepParams, step_registry: StepRegistry
) -> Dict[str, Any]:
    if step["step_type"] is not None:
        raise UnserializableStepError(step_name, step["step_type"])

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

    if step["parallel"]:
        func_map = cast(Dict[str, Callable[[Any], Any]], step["func"])
        encoded["func"] = {
            slot: _name_for_or_raise(step_registry, fn, step_name)
            for slot, fn in func_map.items()
        }
    else:
        func = cast(Callable[[Any], Any], step["func"])
        encoded["func"] = _name_for_or_raise(step_registry, func, step_name)

    branch = step["branch"]
    if branch is not None:
        if callable(branch):
            encoded["branch"] = _name_for_or_raise(step_registry, branch, step_name)
        else:
            encoded["branch"] = {str(key): value for key, value in branch.items()}

    return encoded


def encode_step_function(
    sf: StepFunction, step_registry: Optional[StepRegistry] = None
) -> Dict[str, Any]:
    """Export ``sf`` as a JSON-able dict.

    Recurses into nested sub-step-functions by calling itself again, so
    arbitrary nesting depth is handled without special-casing.

    Raises:
        UnserializableStepError: If any step was built from a BaseStep
            instance (RetryStep, TimeoutStep, WaitStep, or a custom
            BaseStep subclass) — not yet supported.
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

        func_spec = step_data["func"]
        if isinstance(func_spec, dict):
            func: Any = {
                slot: step_registry.get(ref) for slot, ref in func_spec.items()
            }
        else:
            func = step_registry.get(func_spec)

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
        )

    start_step = data.get("start_step")
    if start_step is not None:
        sf.set_start_step(start_step)

    if _validate:
        sf.validate()

    return sf
