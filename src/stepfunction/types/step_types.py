from typing import Any, Callable, Dict, Optional, TypedDict, Union

from stepfunction.constants.enums import StepType


class StepParams(TypedDict):
    func: Union[Callable[[Any], Any], Dict[str, Callable[[Any], Any]]]
    next_step: Optional[str]
    on_failure: Optional[str]
    branch: Optional[Union[Dict[Any, str], Callable[[Any], Optional[str]]]]
    parallel: bool
    stop_on_failure: bool
    is_sub_step_function: bool
    step_type: Optional[StepType]
