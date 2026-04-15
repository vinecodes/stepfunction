"""Module to define the StepFunction class.

Author: Vineeth Penugonda
"""

from asyncio import gather, get_running_loop
from inspect import iscoroutinefunction
from typing import Any, Callable, Dict, Optional, Union, cast

from stepfunction.constants.enums import StepFunctionStatus
from stepfunction.exceptions.step_errors import (
    ParallelStepExecutionError,
    StepExecutionError,
)
from stepfunction.steps.base import BaseStep
from stepfunction.types.step_types import StepParams
from stepfunction.utils.logger import setup_logger


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
    """

    def __init__(self, name: str):
        self.__name = name  # Name of the step function

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
            await sub_step_function.execute(initial_input=last_result)
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
        }

    def set_start_step(self, name: str):
        """Set the start step of the workflow."""
        if name not in self.__steps:
            raise ValueError(f"Step '{name}' not found in steps")

        self.__current_step = name

    def validate(self):
        """Validate the workflow configuration before execution."""

        if self.__current_step is None:
            raise ValueError(
                "No start step set. Call set_start_step() before executing the workflow."
            )

        for step_name, step in self.__steps.items():
            if step["next_step"] is not None and step["next_step"] not in self.__steps:
                raise ValueError(
                    f"Step '{step_name}' has unknown next_step '{step['next_step']}'."
                )
            if (
                step["on_failure"] is not None
                and step["on_failure"] not in self.__steps
            ):
                raise ValueError(
                    f"Step '{step_name}' has unknown on_failure '{step['on_failure']}'."
                )

    async def execute(self, initial_input: Any = None):
        """Execute the workflow."""

        self.validate()

        self.__status = StepFunctionStatus.RUNNING

        self.__logger.debug(
            f"StepFunction - {self.__name} - Status - {self.__status.value}"
        )

        self.__last_result = initial_input

        while self.__current_step:
            step = self.__steps[self.__current_step]
            try:
                if step["parallel"]:
                    results = await self._execute_parallel(
                        cast(Dict[str, Callable[[Any], Any]], step["func"]),
                        step["stop_on_failure"],
                    )

                    self.__last_result = results
                    self.__context[self.__current_step] = results

                    self.__logger.info(
                        f"Parallel step '{self.__current_step}' succeeded with results: {results}"
                    )
                else:
                    result = await self._execute_step(
                        cast(Callable[[Any], Any], step["func"]), self.__last_result
                    )

                    self.__last_result = result
                    self.__context[self.__current_step] = result

                    self.__logger.info(f"Step '{self.__current_step}' succeeded")

                next_step = None

                if step["branch"]:
                    if callable(step["branch"]):
                        next_step = step["branch"](self.__last_result)
                    else:
                        next_step = step["branch"].get(self.__last_result)

                    if next_step is None:
                        self.__logger.warning(
                            f"Step '{self.__current_step}': branch did not resolve to a next step "
                            f"for result '{self.__last_result}'. Workflow will end."
                        )
                    elif next_step not in self.__steps:
                        self.__logger.warning(
                            f"Step '{self.__current_step}': branch resolved to '{next_step}' "
                            "which does not exist in steps. This will cause a failure."
                        )

                self.__current_step = next_step or step["next_step"]

            except Exception as exc:
                self.__logger.exception(
                    f"Step '{self.__current_step}' failed. Exception: {exc}"
                )

                exc_value = exc.args[0] if exc.args else exc

                self.__context[cast(str, self.__current_step)] = exc_value

                if step["on_failure"]:
                    self.__logger.exception(
                        f"Executing failure step: {step['on_failure']} for '{self.__current_step}'"
                    )

                    self.__current_step = step["on_failure"]
                    self.__last_result = exc_value

                    self.__status = StepFunctionStatus.FAILED

                    self.__logger.debug(
                        f"StepFunction - {self.__name} - Status - {self.__status.value}"
                    )
                else:
                    self.__logger.exception(
                        f"No failure step defined for '{self.__current_step}'. Raising Exception."
                    )

                    self.__status = StepFunctionStatus.FAILED

                    self.__logger.debug(
                        f"StepFunction - {self.__name} - Status - {self.__status.value}"
                    )

                    raise StepExecutionError(exc)

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
        self, func_dict: Dict[str, Callable[[Any], Any]], stop_on_failure: bool = False
    ):
        """Execute the steps in parallel without blocking the event loop."""
        loop = get_running_loop()
        results = {}
        errors = []

        async def _run_one(func: Callable[[Any], Any]) -> Any:
            if iscoroutinefunction(func):
                return await func(self.__last_result)
            return await loop.run_in_executor(None, func, self.__last_result)

        task_results = await gather(
            *[_run_one(func) for func in func_dict.values()],
            return_exceptions=True,
        )

        for step_name, result in zip(func_dict.keys(), task_results):
            if isinstance(result, Exception):
                self.__logger.exception(f"Parallel task '{step_name}' failed: {result}")
                results[step_name] = result.args[0] if result.args else result
                errors.append((step_name, result))
            else:
                results[step_name] = result

        if errors:
            self.__logger.error(f"Some parallel tasks failed: {errors}")

            if stop_on_failure:
                self.__status = StepFunctionStatus.FAILED
                raise ParallelStepExecutionError(errors)

        return results

    def visualize(self):
        """Visualize the workflow."""
        from stepfunction.core.visualizer import Visualizer

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

        visualizer = Visualizer(self.__name, self.__steps)

        self.__logger.debug("Visualizing the step function")

        visualizer.visualize_step_function()

        return visualizer.render_step_function_to_string()

    @property
    def name(self):
        """Returns the name of the step function."""
        return self.__name

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

    def __str__(self):
        return f"StepFunction(name={self.__name}, NoOfSteps={len(self.__steps)}, CurrentStep={self.__current_step}, Status={self.__status})"

    def __repr__(self):
        return str(self)
