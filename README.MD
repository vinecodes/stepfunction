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
