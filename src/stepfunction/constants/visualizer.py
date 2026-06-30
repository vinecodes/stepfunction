# Visualizer

# Render Configuration

DEFAULT_VISUALIZER_DIRECTION = "TD"
"""str: The default flowchart direction for the Mermaid visualizer (e.g. TD, LR)."""

DEFAULT_VISUALIZER_EXTENSION = "mmd"
"""str: The default file extension for the visualizer renderer output."""

DEFAULT_VISUALIZER_FOLDER = "workflow_renders"
"""str: The default folder where visualizer renders are stored."""

DEFAULT_VISUALIZER_STRING_ENCODING = "utf-8"
"""str: The default encoding for visualizer strings."""

# Edge labels and colors

DEFAULT_VISUALIZER_SUCCESS_EDGE_LABEL = "Success"
"""str: The default edge label for success transitions in the visualizer."""

DEFAULT_VISUALIZER_FAILURE_EDGE_LABEL = "Failure"
"""str: The default edge label for failure transitions in the visualizer."""

DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_LABEL = "Stop on Failure"
"""str: The default edge label for stop on failure transitions in the visualizer."""

DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_COLOR = "red"
"""str: The default edge color for stop on failure transitions in the visualizer."""

DEFAULT_VISUALIZER_BRANCH_EDGE_LABEL_PREFIX = "Branch"
"""str: The default edge label prefix for branch transitions in the visualizer."""

DEFAULT_VISUALIZER_BRANCH_DEFAULT_LABEL = "else"
"""str: The label used for an unconditional (fallback) branch return."""

DEFAULT_VISUALIZER_MAX_BRANCH_LABEL_LENGTH = 60
"""int: The maximum length of a branch condition label before it's truncated."""

# Node styling (Mermaid classDef names)

DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_CLASS = "subStepFunction"
"""str: The Mermaid classDef name applied to sub-step function nodes."""

DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_CLASS_STYLE = (
    "fill:#f5f5f5,stroke:#333,stroke-dasharray: 5 5"
)
"""str: The Mermaid classDef style applied to sub-step function nodes."""
