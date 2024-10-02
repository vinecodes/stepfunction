# StepFunction

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12%2B-brightgreen.svg)
![Status](https://img.shields.io/badge/Status-Alpha-red.svg)

`StepFunction` is a Python library for orchestrating complex workflows through a step-by-step process. It allows for easy management of sequential and parallel tasks with robust error handling and branching. The library is inspired by AWS Step Functions but implemented as a Python-native solution to orchestrate workflows across any environment.

## Features

- **Sequential and Parallel Execution**: Run steps one after another or in parallel.
- **Error Handling**: Define failure paths and handle exceptions gracefully.
- **Branching Logic**: Direct workflows based on conditions.
- **Sub-Step Functions**: Modularize workflows by embedding sub-step functions.
- **Visualization**: Integrated support for visualizing the workflow graph.

## Installation

You can install the `StepFunction` package using `pip`:

```bash
pip install stepfunction
```

## Documentation and Further Reading

For more detailed usage examples and advanced use cases, please read the [blog post](https://blog.vineethp.com/posts/introducingstepfunction/) that explains the design and usage of the library in-depth. This blog post covers advanced concepts like error handling, sub-step functions, and visualizing workflows in a real-world context.

## Dependencies

The StepFunction package requires the following dependencies:

- `graphviz == 0.20.3`

These will be automatically installed when you install the package via pip.

## Contributing

If you'd like to contribute to StepFunction, feel free to submit issues or pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author
Created and maintained by **Vineeth Penugonda**.

