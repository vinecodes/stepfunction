# StepFunction

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)
![Status](https://img.shields.io/badge/Status-Alpha-red.svg)

`StepFunction` is a Python library for orchestrating complex workflows through a step-by-step process. It allows for easy management of sequential and parallel tasks with robust error handling and branching. The library is inspired by AWS Step Functions but implemented as a Python-native solution to orchestrate workflows across any environment.

## Features

- **Sequential and Parallel Execution**: Run steps one after another or in parallel.
- **Error Handling**: Define failure paths and handle exceptions gracefully.
- **Branching Logic**: Direct workflows based on conditions.
- **Sub-Step Functions**: Modularize workflows by embedding sub-step functions.
- **Visualization**: Integrated support for visualizing the workflow graph as a Mermaid flowchart.
- **Declarative Workflows**: Export a workflow to JSON (`to_dict` / `to_json`) and load it back (`from_dict` / `from_json`) — built-in steps (`TimeoutStep`, `RetryStep`, `WaitStep`) and registered custom steps included, with their settings.
- **Step Parameters**: Give a step fixed settings (`params=`), passed to its function and saved with the workflow — one registered function serves many steps.
- **Lifecycle Hooks**: Get notified as the workflow and each step start, succeed or fail — with inputs, outputs, errors, routing and timings — to record run history, metrics or traces.

## Lifecycle Hooks

Subclass `StepFunctionHooks`, override the events you need (sync or async), and pass an instance to the step function:

```python
from stepfunction.core.step_function import StepFunction
from stepfunction.hooks import StepEvent, StepFunctionHooks


class RunRecorder(StepFunctionHooks):
    async def on_step_start(self, event: StepEvent):
        print(f"{event.workflow}: {event.step} started with {event.input!r}")

    async def on_step_success(self, event: StepEvent):
        print(f"{event.step} -> {event.output!r} in {event.duration:.3f}s, next: {event.next_step}")

    async def on_step_failure(self, event: StepEvent):
        print(f"{event.step} failed: {event.error!r}, next: {event.next_step}")


sf = StepFunction("MyStepFunction", hooks=RunRecorder())
```

Events: `on_workflow_start`, `on_step_start`, `on_step_success`, `on_step_failure`, `on_workflow_end`.

- `StepEvent` carries the workflow path, step name, parallel `task` name (if any), `input`, `output`, the original `error`, the resolved `next_step`, UTC `started_at` / `finished_at` and `duration` in seconds.
- `WorkflowEvent` carries the workflow path, `status`, initial `input`, final `output`, the `error` that ended the run (if `execute()` raised) and timings.
- Each task of a parallel step is reported as its own step event, with `task` set.
- A sub-step function without hooks of its own reports to its parent's hooks; its events carry the nested path, e.g. `"FLOW -> SubStep (SUB_FLOW)"`.
- Hooks observe; they don't steer. An exception raised by a hook is logged and ignored.
- If the run is cancelled, the running step and the workflow are reported with the `CancelledError`, which is then re-raised.

## Declarative Workflows

Register the functions a workflow uses, then export it and load it back:

```python
from stepfunction.registry.step_registry import register_step
from stepfunction.steps import RetryStep, TimeoutStep

register_step("call_api", call_api)

sf = StepFunction("Fetch")
sf.add_step("fetch", TimeoutStep(func=RetryStep(func=call_api, max_retries=3, delay=2), timeout=30))
sf.set_start_step("fetch")

spec = sf.to_dict()
# {"name": "Fetch", "start_step": "fetch", "steps": {"fetch": {..., "step":
#   {"type": "timeout", "timeout": 30,
#    "func": {"type": "retry", "max_retries": 3, "delay": 2, "func": "call_api"}}}}}
rebuilt = StepFunction.from_dict(spec)
```

A step built from a `BaseStep` is stored as `"step": {"type": ..., settings}`; a function it wraps is its registered name, or another step's spec. A parallel step's tasks can be steps too (`{"fetch": RetryStep(...), "log": log_it}`), each stored the same way. To make a custom step exportable, give it a `spec_type`, implement `to_spec` and `from_spec`, and register it with `stepfunction.steps.register_step_type`.

## Step Parameters

A step can carry fixed settings. Its function is then called with them as a second argument, next to the previous step's result, and they are saved in the workflow's JSON:

```python
def block_device(previous, params):
    return f"blocked {previous['device']} for {params['minutes']} min"

register_step("block_device", block_device)

sf.add_step("short_block", block_device, params={"minutes": 10}, next_step="long_block")
sf.add_step("long_block", block_device, params={"minutes": 60})
# to_dict(): "short_block": {"func": "block_device", "params": {"minutes": 10}, ...}
```

A branch router takes settings the same way with `branch_params`, so a condition is data you can store and edit:

```python
def above(result, params):
    return params["then"] if result[params["field"]] > params["above"] else params["else"]

register_step("above", above)
sf.add_step("check", check_usage, branch=above,
            branch_params={"field": "used_mb", "above": 100, "then": "block", "else": "allow"})
# to_dict(): "check": {"func": "check_usage", "branch": "above", "branch_params": {...}, ...}
```

Steps and routers without params are called with the previous result only, as before. `params` must be JSON values; `TimeoutStep` and `RetryStep` pass them on to the function they wrap, and each task of a parallel step gets them.

## Logging

StepFunction logs under the `stepfunction` logger and leaves logging configuration to your application — it never adds handlers to, or changes the level of, the root logger or any other logger. To see its step-by-step messages:

```python
import logging

logging.basicConfig(level=logging.INFO)
```

Without any configuration, Python prints only warnings and errors. Setting the `LOG_LEVEL` environment variable (e.g. `LOG_LEVEL=DEBUG`) sets the level of the `stepfunction` logger only.

## Installation

You can install the `StepFunction` package using `pip`:

```bash
pip install stepfunction
```

## Documentation and Further Reading

For more detailed usage examples and advanced use cases, please read the [blog post](https://blog.vineethp.com/posts/introducingstepfunction/) that explains the design and usage of the library in-depth. This blog post covers advanced concepts like error handling, sub-step functions, and visualizing workflows in a real-world context.

## Dependencies

The StepFunction package has no required runtime dependencies. Workflow visualization renders directly to [Mermaid](https://mermaid.js.org/) flowchart syntax (`.mmd`), which can be previewed in VS Code, GitHub/Bitbucket markdown, or https://mermaid.live without any additional tooling.

## Contributing

If you'd like to contribute to StepFunction, feel free to submit issues or pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author
Created and maintained by **Vineeth Penugonda**.
