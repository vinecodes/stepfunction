from typing import Any, Callable, Dict, Optional, TypedDict


class StepParams(TypedDict, total=False):

    func: Callable[[Any], Any]
    next_step: Optional[str]
    on_failure: Optional[str]
    branch: Optional[Dict[Any, str]]
    parallel: bool
    stop_on_failure: bool
    is_sub_step_function: bool
