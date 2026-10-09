"""Events passed to lifecycle hooks.

Author: Vineeth Penugonda
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from stepfunction.constants.enums import StepFunctionStatus


@dataclass(frozen=True)
class StepEvent:
    """Describes one step (or one task of a parallel step) as it starts or ends.

    Attributes:
        workflow (str): Path of the step function running the step, from the
            outermost workflow down, e.g. "FLOW -> SubStep (SUB_FLOW)".
        step (str): Name of the step.
        task (Optional[str]): Name of the task within a parallel step; None for
            ordinary steps and for the parallel step itself.
        input (Any): The value the step was called with.
        started_at (datetime): When the step started (UTC).
        output (Any): The step's result. Set on success only.
        error (Optional[BaseException]): The exception the step raised. Set on
            failure only — the original exception, not the value stored in context.
        next_step (Optional[str]): Where the workflow goes next: the branch or
            next_step target on success, the on_failure target on failure, or
            None if the workflow ends (or raises) here.
        finished_at (Optional[datetime]): When the step ended (UTC). None on start.
        duration (Optional[float]): Seconds the step took, from a monotonic
            clock. None on start.
    """

    workflow: str
    step: str
    task: Optional[str]
    input: Any
    started_at: datetime
    output: Any = None
    error: Optional[BaseException] = None
    next_step: Optional[str] = None
    finished_at: Optional[datetime] = None
    duration: Optional[float] = None


@dataclass(frozen=True)
class WorkflowEvent:
    """Describes a step function run as it starts or ends.

    Attributes:
        workflow (str): Path of the step function, from the outermost workflow down.
        status (StepFunctionStatus): RUNNING on start; COMPLETED or FAILED on end.
        input (Any): The initial input the run was called with.
        started_at (datetime): When the run started (UTC).
        output (Any): The last step's result. Set on end only.
        error (Optional[BaseException]): The exception execute() raised (e.g. a
            StepExecutionError wrapping the step's error — the step's own failure
            event has the original). None when the run completed, or failed into
            an on_failure step.
        finished_at (Optional[datetime]): When the run ended (UTC). None on start.
        duration (Optional[float]): Seconds the run took. None on start.
    """

    workflow: str
    status: StepFunctionStatus
    input: Any
    started_at: datetime
    output: Any = None
    error: Optional[BaseException] = None
    finished_at: Optional[datetime] = None
    duration: Optional[float] = None
