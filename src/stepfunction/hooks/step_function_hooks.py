"""Base class for observing a step function's lifecycle.

Author: Vineeth Penugonda
"""

from stepfunction.hooks.events import StepEvent, WorkflowEvent


class StepFunctionHooks:
    """Receives events as a step function runs.

    Subclass it and override the methods you need; the rest do nothing. Each
    method may be a regular function or a coroutine function. Pass an instance
    to ``StepFunction(name, hooks=...)`` or ``set_hooks()``.

    Hooks observe; they don't steer. An exception raised by a hook is logged
    and ignored, so it never changes the workflow's routing or status. A
    sub-step function without hooks of its own uses its parent's.

    Order of events for one run:
        on_workflow_start
        for each step: on_step_start, then on_step_success or on_step_failure
            (a parallel step also reports each task between its own start and end,
            with ``event.task`` set)
        on_workflow_end

    If the run is cancelled, the running step and the workflow end with
    ``error`` set to the ``asyncio.CancelledError``, which is then re-raised.

    Example:
        class PrintHooks(StepFunctionHooks):
            async def on_step_success(self, event: StepEvent):
                print(f"{event.step} took {event.duration:.3f}s -> {event.next_step}")

        sf = StepFunction("MyStepFunction", hooks=PrintHooks())
    """

    def on_workflow_start(self, event: WorkflowEvent):
        """Called once the workflow is validated, before its first step."""

    def on_workflow_end(self, event: WorkflowEvent):
        """Called when the workflow completes, fails, raises or is cancelled."""

    def on_step_start(self, event: StepEvent):
        """Called before a step (or a parallel task) runs."""

    def on_step_success(self, event: StepEvent):
        """Called after a step (or a parallel task) returns and its next step is resolved."""

    def on_step_failure(self, event: StepEvent):
        """Called after a step (or a parallel task) raises."""
