"""Module to define the StepFunction class.

Author: Vineeth Penugonda
"""

from asyncio import CancelledError, gather, get_running_loop
from inspect import isawaitable, iscoroutinefunction
from time import monotonic
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union, cast

from stepfunction.constants.enums import StepFunctionStatus
from stepfunction.exceptions.step_errors import (
    ParallelStepExecutionError,
    StepExecutionError,
)
from stepfunction.hooks import StepEvent, StepFunctionHooks, WorkflowEvent
from stepfunction.steps.base import BaseStep
from stepfunction.types.step_types import StepParams
from stepfunction.utils.logger import setup_logger
from stepfunction.utils.utils import utc_now

if TYPE_CHECKING:
    from stepfunction.registry.step_registry import StepRegistry


class StepFunction:
    """
    Class to represent a workflow consisting of multiple steps.

    This class allows for sequential and parallel execution of steps in a workflow. Each step can have a next step to
    proceed to upon success, an on_failure step to proceed to in case of failure, and optional branching based on the
    result of a step. Parallel steps can be executed concurrently, with the option to stop all parallel executions
    if one of them fails. The results of each step, including failures, are stored in the workflow's context, which can
    be visualized or retrieved for further analysis.

    Attributes:
        current_step (Optional[str]): The current step being executed.
        context (Dict[str, Any]): A dictionary that holds the results of each step, including exceptions if any occur.

    Properties:
        name (str): The name of the step function.
        hooks (Optional[StepFunctionHooks]): The lifecycle hooks set on this step function, if any.
        steps (Dict[str, StepParams]): A dictionary containing the steps of the workflow.
        last_result (Any): The result of the last step.
        context (Dict[str, Any]): Stores step names and results, including exceptions if any occur.
        status (StepFunctionStatus): The current status of the workflow. Possible values are:
            - StepFunctionStatus.INITIALIZED: The workflow is initialized but not yet started.
            - StepFunctionStatus.RUNNING: The workflow is currently in progress.
            - StepFunctionStatus.COMPLETED: The workflow finished successfully.
            - StepFunctionStatus.FAILED: The workflow encountered an error and went to a failure handler or failed entirely.

    Methods:
        add_step(name, func, next_step=None, on_failure=None, branch=None, parallel=False, stop_on_failure=False):
            Add a step to the workflow.

        set_start_step(name):
            Set the start step of the workflow.

        set_hooks(hooks):
            Set the lifecycle hooks (a StepFunctionHooks) notified as steps start, succeed and fail.

        add_sub_step_function(name, sub_step_function, next_step=None, on_failure=None):
            Add a sub-step function to be executed as a step.

        validate():
            Validate the workflow configuration. Raises ValueError if the start step is not set
            or if any next_step or on_failure reference an unknown step.

        execute(initial_input=None):
            Execute the workflow starting from the specified start step. This will run each step in sequence or in parallel,
            depending on the step configuration.

        visualize():
            Visualize the workflow structure and the relationships between steps.

        visualize_to_string():
            Return a string representation of the workflow for visualization.

        to_dict(step_registry=None) / to_json(indent=2, step_registry=None):
            Export the workflow as a JSON-able dict / JSON string, resolving step and
            branch functions to their registered name via stepfunction.registry.step_registry.

        from_dict(data, step_registry=None) / from_json(json_str, step_registry=None):
            Classmethods that reconstruct a StepFunction from a dict/JSON string
            produced by to_dict()/to_json(), resolving function names via the registry.

    Protected Methods:
        _execute_step(func, input_value):
            Execute a single step, handling asynchronous and synchronous functions appropriately.

        _execute_parallel(func_dict, stop_on_failure=False):
            Execute parallel steps concurrently. Store the results for each step in the context, including exceptions
            if any step fails. If `stop_on_failure` is True, halt all parallel executions if one of the steps fails.

    Raises:
        ValueError:
            Raised if a step with the same name already exists in the workflow or if an undefined step is set as the start step.

        StepExecutionError:
            Raised when a step fails and no `on_failure` step is defined.

        ParallelStepExecutionError:
            Raised when one or more parallel steps fail and `stop_on_failure` is set to True.

    Example usage:
        step_function = StepFunction("MyStepFunction")
        step_function.add_step("Step1", func1, next_step="Step2")
        step_function.add_step("Step2", func2, branch={"success": "Step3", "failure": "Step4"})
        step_function.add_step("Step3", func3, on_failure="Step1")
        step_function.add_step("Step4", func4)
        step_function.set_start_step("Step1")
        await step_function.execute()

    Parallel Example:
        step_function.add_step("Step1", func1, next_step="ParallelStep")
        step_function.add_step("ParallelStep", {
            "task1": func2,
            "task2": func3
        }, parallel=True)

    Sub-step function example:
        sub_step_function = StepFunction("SubStepFunction")
        # Define steps for sub_step_function...
        step_function.add_sub_step_function("SubStep", sub_step_function, next_step="FinalStep")
        await step_function.execute()

    Status Example:
        status = step_function.status  # Will be StepFunctionStatus.INITIALIZED, StepFunctionStatus.RUNNING, StepFunctionStatus.COMPLETED, or StepFunctionStatus.FAILED.

    Hooks Example:
        class RunRecorder(StepFunctionHooks):
            async def on_step_success(self, event):
                print(event.step, event.duration, event.next_step)

        step_function = StepFunction("MyStepFunction", hooks=RunRecorder())
    """

    def __init__(self, name: str, hooks: Optional[StepFunctionHooks] = None):
        self.__name = name  # Name of the step function

        self.__hooks = hooks  # Lifecycle hooks set on this step function

        # Hooks and workflow path for the current run; a sub-step function
        # without hooks of its own inherits its parent's
        self.__run_hooks: Optional[StepFunctionHooks] = None
        self.__run_path: List[str] = [name]

        self.__steps: Dict[str, StepParams] = {}  # Steps of the workflow
        self.__current_step = None  # The current step being executed

        self.__last_result = None  # To hold the result of the last step
        self.__context: Dict[
            str, Any
        ] = {}  # To hold the step names and results of those steps

        # Status of the step function
        self.__status: StepFunctionStatus = StepFunctionStatus.INITIALIZED

        self.__logger = setup_logger(__name__)

        self.__logger.debug(
            f"StepFunction - {self.__name} - Status - {self.__status.value}"
        )

    def add_step(
        self,
        name: str,
        func: Union[Callable[[Any], Any], Dict[str, Callable[[Any], Any]], BaseStep],
        next_step: Optional[str] = None,
        on_failure: Optional[str] = None,
        branch: Optional[Union[Dict[Any, str], Callable[[Any], str]]] = None,
        parallel: bool = False,
        stop_on_failure: bool = False,
    ):
        """Add a step to the workflow."""

        if name in self.__steps:
            raise ValueError(f"Step '{name}' already exists in steps")

        if branch is not None and next_step is not None:
            raise ValueError(
                f"Step '{name}' cannot have both 'branch' and 'next_step' set. "
                "Use 'branch' to control routing or 'next_step' for a fixed transition, not both."
            )

        step_type = None
        if isinstance(func, BaseStep):
            step_type = func.step_type
            func = func.build()

        self.__steps[name] = {
            "func": func,
            "next_step": next_step,
            "on_failure": on_failure,
            "branch": branch,
            "parallel": parallel,
            "stop_on_failure": stop_on_failure,
            "is_sub_step_function": False,
            "step_type": step_type,
            "sub_step_function": None,
        }

    def add_sub_step_function(
        self,
        name: str,
        sub_step_function: "StepFunction",
        next_step: Optional[str] = None,
        on_failure: Optional[str] = None,
    ):
        """Add a sub-step function to the workflow."""

        if name in self.__steps:
            raise ValueError(f"Step '{name}' already exists in steps")

        async def sub_func(last_result):
            await sub_step_function._execute(
                initial_input=last_result,
                hooks=sub_step_function.hooks
                if sub_step_function.hooks is not None
                else self.__run_hooks,
                path=self.__run_path + [_sub_path_label(name, sub_step_function)],
            )
            self.__context.update(sub_step_function.context)

            if sub_step_function.status == StepFunctionStatus.FAILED:
                self.__status = StepFunctionStatus.FAILED

            return sub_step_function.last_result

        self.__steps[name] = {
            "func": sub_func,
            "next_step": next_step,
            "on_failure": on_failure,
            "branch": None,
            "parallel": False,
            "stop_on_failure": False,
            "is_sub_step_function": True,
            "step_type": None,
            "sub_step_function": sub_step_function,
        }

    def set_start_step(self, name: str):
        """Set the start step of the workflow."""
        if name not in self.__steps:
            raise ValueError(f"Step '{name}' not found in steps")

        self.__current_step = name

    def set_hooks(self, hooks: Optional[StepFunctionHooks]):
        """Set the lifecycle hooks notified as the workflow runs (None removes them)."""
        self.__hooks = hooks

    def validate(self):
        """Validate the workflow configuration before execution."""
        self._validate(path=[self.__name])

    def _validate(self, path: List[str]):
        """Validate this step function, recursing into sub-step functions.

        ``path`` tracks the chain of step-function names from the outermost
        workflow down to this one, so a failure several sub-step functions
        deep is reported as a single readable breadcrumb (e.g.
        "FLOW -> SUB_FLOW_3 -> SUB_FLOW_4") instead of a wall of nested
        "invalid sub-step function" messages.
        """

        def _fail(message: str) -> None:
            location = " -> ".join(path)
            raise ValueError(f"[{location}] {message}")

        if self.__current_step is None:
            _fail(
                "No start step set. Call set_start_step() before executing the workflow."
            )

        for step_name, step in self.__steps.items():
            if step["next_step"] is not None and step["next_step"] not in self.__steps:
                _fail(
                    f"Step '{step_name}' has unknown next_step '{step['next_step']}'."
                )
            if (
                step["on_failure"] is not None
                and step["on_failure"] not in self.__steps
            ):
                _fail(
                    f"Step '{step_name}' has unknown on_failure '{step['on_failure']}'."
                )
            if step["is_sub_step_function"]:
                sub_step_function = cast("StepFunction", step["sub_step_function"])
                sub_step_function._validate(
                    path=path + [_sub_path_label(step_name, sub_step_function)]
                )

    async def execute(self, initial_input: Any = None):
        """Execute the workflow."""

        await self._execute(initial_input, hooks=self.__hooks, path=[self.__name])

    async def _execute(
        self,
        initial_input: Any,
        hooks: Optional[StepFunctionHooks],
        path: List[str],
    ):
        """Execute the workflow, reporting to ``hooks`` under the workflow ``path``.

        ``path`` is the chain of step-function names from the outermost
        workflow down to this one, as in _validate(); sub-step functions are
        run through here so their events carry the full path.
        """

        self.validate()

        self.__run_hooks = hooks
        self.__run_path = path
        workflow = " -> ".join(path)

        self.__status = StepFunctionStatus.RUNNING

        self.__logger.debug(
            f"StepFunction - {self.__name} - Status - {self.__status.value}"
        )

        self.__last_result = initial_input

        run_started_at = utc_now()
        run_started = monotonic()
        await self._emit(
            "on_workflow_start",
            WorkflowEvent(
                workflow=workflow,
                status=self.__status,
                input=initial_input,
                started_at=run_started_at,
            ),
        )

        run_error: Optional[BaseException] = None
        try:
            while self.__current_step:
                await self._execute_current_step(workflow)
        except BaseException as exc:
            run_error = exc
            self.__status = StepFunctionStatus.FAILED
            raise
        finally:
            await self._emit(
                "on_workflow_end",
                WorkflowEvent(
                    workflow=workflow,
                    status=self.__status,
                    input=initial_input,
                    started_at=run_started_at,
                    output=self.__last_result,
                    error=run_error,
                    finished_at=utc_now(),
                    duration=monotonic() - run_started,
                ),
            )

    async def _execute_current_step(self, workflow: str):
        """Execute the current step, route to the next one and report both to the hooks."""

        step_name = cast(str, self.__current_step)
        step = self.__steps[step_name]
        step_input = self.__last_result

        started_at = utc_now()
        started = monotonic()
        await self._emit(
            "on_step_start",
            StepEvent(
                workflow=workflow,
                step=step_name,
                task=None,
                input=step_input,
                started_at=started_at,
            ),
        )

        def _ended(**fields: Any) -> StepEvent:
            return StepEvent(
                workflow=workflow,
                step=step_name,
                task=None,
                input=step_input,
                started_at=started_at,
                finished_at=utc_now(),
                duration=monotonic() - started,
                **fields,
            )

        try:
            if step["parallel"]:
                results = await self._execute_parallel(
                    cast(Dict[str, Callable[[Any], Any]], step["func"]),
                    step["stop_on_failure"],
                    workflow=workflow,
                    step_name=step_name,
                )

                self.__last_result = results
                self.__context[step_name] = results

                self.__logger.info(
                    f"Parallel step '{step_name}' succeeded with results: {results}"
                )
            else:
                result = await self._execute_step(
                    cast(Callable[[Any], Any], step["func"]), self.__last_result
                )

                self.__last_result = result
                self.__context[step_name] = result

                self.__logger.info(f"Step '{step_name}' succeeded")

            next_step = None

            if step["branch"]:
                if callable(step["branch"]):
                    next_step = step["branch"](self.__last_result)
                else:
                    next_step = step["branch"].get(self.__last_result)

                if next_step is None:
                    self.__logger.warning(
                        f"Step '{step_name}': branch did not resolve to a next step "
                        f"for result '{self.__last_result}'. Workflow will end."
                    )
                elif next_step not in self.__steps:
                    self.__logger.warning(
                        f"Step '{step_name}': branch resolved to '{next_step}' "
                        "which does not exist in steps. This will cause a failure."
                    )

            self.__current_step = next_step or step["next_step"]

        except CancelledError as exc:
            self.__logger.warning(f"Step '{step_name}' was cancelled")

            self.__status = StepFunctionStatus.FAILED

            await self._emit("on_step_failure", _ended(error=exc))

            raise

        except Exception as exc:
            self.__logger.exception(f"Step '{step_name}' failed. Exception: {exc}")

            exc_value = exc.args[0] if exc.args else exc

            self.__context[step_name] = exc_value

            self.__status = StepFunctionStatus.FAILED

            self.__logger.debug(
                f"StepFunction - {self.__name} - Status - {self.__status.value}"
            )

            await self._emit(
                "on_step_failure", _ended(error=exc, next_step=step["on_failure"])
            )

            if step["on_failure"]:
                self.__logger.exception(
                    f"Executing failure step: {step['on_failure']} for '{step_name}'"
                )

                self.__current_step = step["on_failure"]
                self.__last_result = exc_value
            else:
                self.__logger.exception(
                    f"No failure step defined for '{step_name}'. Raising Exception."
                )

                raise StepExecutionError(exc)

        else:
            await self._emit(
                "on_step_success",
                _ended(output=self.__last_result, next_step=self.__current_step),
            )

        if not self.__current_step and self.__status != StepFunctionStatus.FAILED:
            # If no more steps, mark as COMPLETED

            self.__status = StepFunctionStatus.COMPLETED

            self.__logger.debug(
                f"StepFunction - {self.__name} - Status - {self.__status.value}"
            )

    async def _execute_step(self, func: Callable, input_value: Any):
        """Execute a single step, handling async functions."""
        if iscoroutinefunction(func):
            return await func(input_value)
        else:
            return func(input_value)

    async def _execute_parallel(
        self,
        func_dict: Dict[str, Callable[[Any], Any]],
        stop_on_failure: bool = False,
        workflow: Optional[str] = None,
        step_name: Optional[str] = None,
    ):
        """Execute the steps in parallel without blocking the event loop.

        Each task is reported to the hooks as its own step event, with
        ``task`` set to its name.
        """
        loop = get_running_loop()
        results = {}
        errors = []
        step_input = self.__last_result

        async def _run_one(task: str, func: Callable[[Any], Any]) -> Any:
            started_at = utc_now()
            started = monotonic()
            await self._emit(
                "on_step_start",
                StepEvent(
                    workflow=cast(str, workflow),
                    step=cast(str, step_name),
                    task=task,
                    input=step_input,
                    started_at=started_at,
                ),
            )

            def _ended(**fields: Any) -> StepEvent:
                return StepEvent(
                    workflow=cast(str, workflow),
                    step=cast(str, step_name),
                    task=task,
                    input=step_input,
                    started_at=started_at,
                    finished_at=utc_now(),
                    duration=monotonic() - started,
                    **fields,
                )

            try:
                if iscoroutinefunction(func):
                    result = await func(step_input)
                else:
                    result = await loop.run_in_executor(None, func, step_input)
            except BaseException as exc:
                await self._emit("on_step_failure", _ended(error=exc))
                raise

            await self._emit("on_step_success", _ended(output=result))
            return result

        task_results = await gather(
            *[_run_one(task, func) for task, func in func_dict.items()],
            return_exceptions=True,
        )

        for task, result in zip(func_dict.keys(), task_results):
            if isinstance(result, Exception):
                self.__logger.exception(f"Parallel task '{task}' failed: {result}")
                results[task] = result.args[0] if result.args else result
                errors.append((task, result))
            else:
                results[task] = result

        if errors:
            self.__logger.error(f"Some parallel tasks failed: {errors}")

            if stop_on_failure:
                self.__status = StepFunctionStatus.FAILED
                raise ParallelStepExecutionError(errors)

        return results

    async def _emit(self, hook_name: str, event: Union[StepEvent, WorkflowEvent]):
        """Call a hook for this run, awaiting it if it's a coroutine.

        A hook that raises is logged and ignored: hooks observe the workflow,
        they never change its routing or status.
        """
        hooks = self.__run_hooks
        if hooks is None:
            return

        try:
            result = getattr(hooks, hook_name)(event)
            if isawaitable(result):
                await result
        except Exception:
            self.__logger.exception(
                f"StepFunction - {self.__name} - Hook '{hook_name}' raised; ignoring"
            )

    def visualize(self):
        """Visualize the workflow."""
        from stepfunction.core.visualizer import Visualizer

        self.validate()

        visualizer = Visualizer(self.__name, self.__steps)

        self.__logger.debug("Visualizing the step function")

        visualizer.visualize_step_function()

        self.__logger.debug("Rendering the step function")

        visualizer.render_step_function()

        output_file_name = visualizer.output_file_name

        self.__logger.debug(f"Rendered the step function to file: {output_file_name}")

    def visualize_to_string(self):
        """Visualize the workflow as a string."""
        from stepfunction.core.visualizer import Visualizer

        self.validate()

        visualizer = Visualizer(self.__name, self.__steps)

        self.__logger.debug("Visualizing the step function")

        visualizer.visualize_step_function()

        return visualizer.render_step_function_to_string()

    def to_dict(self, step_registry: Optional["StepRegistry"] = None) -> Dict[str, Any]:
        """Export this workflow as a JSON-able dict.

        Function references (step funcs, parallel-step funcs, and branch
        callables) are encoded as their registered string name — see
        ``stepfunction.registry.step_registry``. Nested sub-step-functions are
        encoded recursively.

        Call this before execute(): if the workflow has already run,
        "start_step" reflects wherever the execution cursor ended up
        (often None after a completed run), not the original start step.

        Raises:
            UnserializableStepError: If any step was built from a BaseStep
                instance (RetryStep, TimeoutStep, WaitStep, or a custom
                BaseStep subclass) — not yet supported.
            UnregisteredFunctionError: If a step or branch function used in
                this workflow has no registered name in ``step_registry``.
        """
        from stepfunction.core.serializer import encode_step_function

        return encode_step_function(self, step_registry)

    def to_json(
        self, indent: Optional[int] = 2, step_registry: Optional["StepRegistry"] = None
    ) -> str:
        """Export this workflow as a JSON string. See to_dict() for details
        and caveats."""
        from json import dumps

        return dumps(self.to_dict(step_registry), indent=indent)

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], step_registry: Optional["StepRegistry"] = None
    ) -> "StepFunction":
        """Reconstruct a StepFunction from a dict produced by to_dict().

        Function name references in ``data`` are resolved against
        ``step_registry`` (defaults to the package's default registry,
        ``stepfunction.registry.step_registry.registry``, if not given). Validates the
        reconstructed workflow before returning, so a malformed spec fails
        fast with a readable breadcrumb error rather than only failing
        later at execute() time.

        Raises:
            UnregisteredFunctionError: If a referenced function name isn't
                registered.
            ValueError: If the reconstructed workflow fails validate().
        """
        from stepfunction.core.serializer import decode_step_function

        return decode_step_function(data, step_registry)

    @classmethod
    def from_json(
        cls, json_str: str, step_registry: Optional["StepRegistry"] = None
    ) -> "StepFunction":
        """Reconstruct a StepFunction from a JSON string produced by to_json().
        See from_dict() for details."""
        from json import loads

        return cls.from_dict(loads(json_str), step_registry)

    @property
    def name(self):
        """Returns the name of the step function."""
        return self.__name

    @property
    def hooks(self) -> Optional[StepFunctionHooks]:
        """Returns the lifecycle hooks set on the step function, if any."""
        return self.__hooks

    @property
    def steps(self):
        """Returns the steps of the step function."""
        return self.__steps.copy()

    @property
    def last_result(self):
        """Returns the result of the last step."""
        return self.__last_result

    @property
    def context(self):
        """Returns the context of the step function."""
        return self.__context.copy()

    @property
    def status(self):
        """Returns the status of the step function."""
        return self.__status

    @property
    def current_step(self):
        """Returns the step set by set_start_step(), advanced by execute()
        as the workflow progresses."""
        return self.__current_step

    def __str__(self):
        return f"StepFunction(name={self.__name}, NoOfSteps={len(self.__steps)}, CurrentStep={self.__current_step}, Status={self.__status})"

    def __repr__(self):
        return str(self)


def _sub_path_label(step_name: str, sub_step_function: StepFunction) -> str:
    """How a sub-step function appears in a workflow path: its step name, plus
    its own name when the two differ (e.g. "SubStep (SUB_FLOW)")."""
    if step_name != sub_step_function.name:
        return f"{step_name} ({sub_step_function.name})"
    return step_name
