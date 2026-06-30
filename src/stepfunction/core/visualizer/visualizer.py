"""This module contains the visualizer class for the graph model.

Author: Vineeth Penugonda
"""

from ast import (
    AST,
    AsyncFunctionDef,
    Constant,
    FunctionDef,
    If,
    Lambda,
    Return,
    iter_child_nodes,
    parse,
    unparse,
    walk,
)
from inspect import getsource
from os import getcwd, makedirs
from re import sub as re_sub
from textwrap import dedent
from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple, cast

from stepfunction.constants.visualizer import (
    DEFAULT_VISUALIZER_BRANCH_DEFAULT_LABEL,
    DEFAULT_VISUALIZER_BRANCH_EDGE_LABEL_PREFIX,
    DEFAULT_VISUALIZER_DIRECTION,
    DEFAULT_VISUALIZER_EXTENSION,
    DEFAULT_VISUALIZER_FAILURE_EDGE_LABEL,
    DEFAULT_VISUALIZER_FOLDER,
    DEFAULT_VISUALIZER_MAX_BRANCH_LABEL_LENGTH,
    DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_COLOR,
    DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_LABEL,
    DEFAULT_VISUALIZER_STRING_ENCODING,
    DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_CLASS,
    DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_CLASS_STYLE,
    DEFAULT_VISUALIZER_SUCCESS_EDGE_LABEL,
    VISUALIZER_INVALID_NODE_ID_CHARS,
)
from stepfunction.types.step_types import StepParams


def _quote(label: str) -> str:
    """Escape and quote a string for use as a Mermaid edge label."""

    escaped = label.replace('"', "'").replace("|", "/")
    return f'"{escaped}"'


def _truncate(
    label: str, max_length: int = DEFAULT_VISUALIZER_MAX_BRANCH_LABEL_LENGTH
) -> str:
    """Truncate a label to a maximum length, preserving readability."""

    if len(label) <= max_length:
        return label

    return f"{label[: max_length - 3]}..."


def _extract_callable_branch_edges(
    branch_func: Callable[[Any], Optional[str]], known_steps: Set[str]
) -> List[Tuple[str, Optional[str]]]:
    """Statically inspects a branch callable's source for ``return "<step_name>"``
    statements, pairing each target with the nearest enclosing ``if``/``else``
    condition.

    Router callables in this library are plain functions that inspect the prior
    step's result and return the name of the next step. Since the callable isn't
    executed at visualization time, the runtime outcome can't be known - but most
    routers are simple if/elif/return chains, so a light AST scan recovers a
    faithful approximation of the possible branches without executing the
    callable. Falls back to no edges if the source isn't available or isn't a
    recognizable if/return shape, rather than guessing.

    Returns a list of ``(target_step, condition_label)`` tuples, where
    ``condition_label`` is ``None`` for an unconditional/fallback return.
    """

    try:
        source = dedent(getsource(branch_func))
        tree = parse(source)
    except (OSError, TypeError, SyntaxError):
        return []

    func_node = next(
        (
            node
            for node in walk(tree)
            if isinstance(node, (FunctionDef, AsyncFunctionDef))
        ),
        None,
    )
    if func_node is None:
        return []

    # Map each node in the function body to the nearest enclosing `if` *and*
    # which side of it the node is on (the `test` body vs. the `else`/`elif`
    # body) - a plain `if/else` shares one `If` node for both branches, so
    # without tracking the side, a return in the `else` would be mislabeled
    # with the same (un-negated) condition as the `if` branch.
    branch_context: Dict[AST, Optional[Tuple[If, bool]]] = {}

    def _walk(node: AST, current_branch: Optional[Tuple[If, bool]]) -> None:
        if isinstance(node, If):
            branch_context[node] = current_branch

            for child in node.body:
                branch_context[child] = (node, True)
                _walk(child, (node, True))

            for child in node.orelse:
                branch_context[child] = (node, False)
                _walk(child, (node, False))

            return

        for child in iter_child_nodes(node):
            if isinstance(child, (FunctionDef, AsyncFunctionDef, Lambda)):
                continue

            branch_context[child] = current_branch
            _walk(child, current_branch)

    _walk(func_node, None)

    edges: List[Tuple[str, Optional[str]]] = []
    seen: Set[Tuple[str, Optional[str]]] = set()

    for node in walk(func_node):
        if not isinstance(node, Return) or node.value is None:
            continue

        value = node.value
        if not (isinstance(value, Constant) and isinstance(value.value, str)):
            continue

        target = value.value
        if target not in known_steps:
            continue

        context = branch_context.get(node)
        label = None
        if context is not None:
            enclosing_if, is_true_branch = context
            try:
                condition = unparse(enclosing_if.test)
                label = condition if is_true_branch else f"not ({condition})"
            except Exception:
                label = None

        key = (target, label)
        if key in seen:
            continue

        seen.add(key)
        edges.append((target, label))

    return edges


class Visualizer:
    """This class is responsible for visualizing the graph model as a Mermaid flowchart."""

    def __init__(self, graph_name: str, steps: Optional[Dict[str, StepParams]] = None):
        """Initializes the visualizer."""

        self.graph_name = graph_name
        self.__steps = steps

        self.__output_file_name = None
        self.__output_file_path = None

        self.__node_lines: List[str] = []
        self.__edge_lines: List[str] = []
        self.__link_styles: List[str] = []
        self.__sub_step_function_nodes: Set[str] = set()
        self.__node_ids: Dict[str, str] = {}

    def visualize_step_function(self):
        """Builds the Mermaid flowchart definition from the step function's steps."""

        if not self.__steps:
            raise ValueError("No steps found to visualize.")

        known_steps = set(self.__steps.keys())

        for step_name, step_info in self.__steps.items():
            self.__add_node(step_name, step_info)

            if step_info["next_step"]:
                self.__add_edge(
                    step_name,
                    step_info["next_step"],
                    DEFAULT_VISUALIZER_SUCCESS_EDGE_LABEL,
                )

            if step_info["on_failure"]:
                if step_info.get("stop_on_failure"):
                    self.__add_edge(
                        step_name,
                        step_info["on_failure"],
                        DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_LABEL,
                        dashed=True,
                        color=DEFAULT_VISUALIZER_STOP_ON_FAILURE_EDGE_COLOR,
                    )
                else:
                    self.__add_edge(
                        step_name,
                        step_info["on_failure"],
                        DEFAULT_VISUALIZER_FAILURE_EDGE_LABEL,
                        dashed=True,
                    )

            if step_info["parallel"]:
                # func is a dictionary for parallel steps
                parallel_function_names = cast(
                    Dict[str, Callable[[Any], Any]], step_info["func"]
                )

                for parallel_step_name in parallel_function_names:
                    self.__add_node(parallel_step_name, {})
                    self.__add_edge(step_name, parallel_step_name, dashed=True)

                    if step_info["next_step"]:
                        self.__add_edge(parallel_step_name, step_info["next_step"])

            branch = step_info["branch"]
            if isinstance(branch, dict):
                for result, next_step in branch.items():
                    self.__add_edge(
                        step_name,
                        next_step,
                        f"{DEFAULT_VISUALIZER_BRANCH_EDGE_LABEL_PREFIX}: {result}",
                    )
            elif callable(branch):
                for target, condition in _extract_callable_branch_edges(
                    branch, known_steps
                ):
                    label_suffix = condition or DEFAULT_VISUALIZER_BRANCH_DEFAULT_LABEL
                    label = (
                        f"{DEFAULT_VISUALIZER_BRANCH_EDGE_LABEL_PREFIX}: "
                        f"{_truncate(label_suffix)}"
                    )
                    self.__add_edge(step_name, target, label)

    def __node_id(self, step_name: str) -> str:
        """Maps a step name to a Mermaid-safe node ID.

        Step names are free text and may contain spaces or other characters
        that Mermaid doesn't allow in a bare node ID (only the bracketed label
        accepts arbitrary text). The original name is preserved as the node's
        label; this only affects the identifier used to reference the node in
        edges. Cached so the same step name always resolves to the same ID,
        and disambiguated on collision (e.g. "First Step" and "First_Step"
        would otherwise both sanitize to "First_Step").
        """

        if step_name in self.__node_ids:
            return self.__node_ids[step_name]

        sanitized = re_sub(VISUALIZER_INVALID_NODE_ID_CHARS, "_", step_name) or "step"
        if sanitized[0].isdigit():
            sanitized = f"_{sanitized}"

        existing_ids = set(self.__node_ids.values())
        candidate = sanitized
        suffix = 2
        while candidate in existing_ids:
            candidate = f"{sanitized}_{suffix}"
            suffix += 1

        self.__node_ids[step_name] = candidate
        return candidate

    def __add_node(self, step_name: str, step_info: Mapping[str, Any]) -> None:
        node_id = self.__node_id(step_name)

        if step_info.get("is_sub_step_function"):
            self.__node_lines.append(f"{node_id}([{_quote(step_name)}])")
            self.__sub_step_function_nodes.add(node_id)
        else:
            self.__node_lines.append(f"{node_id}[{_quote(step_name)}]")

    def __add_edge(
        self,
        source: str,
        target: str,
        label: Optional[str] = None,
        dashed: bool = False,
        color: Optional[str] = None,
    ) -> None:
        arrow = "-.->" if dashed else "-->"
        source_id = self.__node_id(source)
        target_id = self.__node_id(target)

        if label:
            self.__edge_lines.append(
                f"{source_id} {arrow}|{_quote(label)}| {target_id}"
            )
        else:
            self.__edge_lines.append(f"{source_id} {arrow} {target_id}")

        if color:
            edge_index = len(self.__edge_lines) - 1
            self.__link_styles.append(f"linkStyle {edge_index} stroke:{color}")

    def __build_mermaid(self, direction: str) -> str:
        lines = [f"flowchart {direction}"]

        lines.extend(f"    {line}" for line in self.__node_lines)
        lines.extend(f"    {line}" for line in self.__edge_lines)
        lines.extend(f"    {line}" for line in self.__link_styles)

        if self.__sub_step_function_nodes:
            lines.append(
                f"    classDef {DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_CLASS} "
                f"{DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_CLASS_STYLE}"
            )
            node_list = ",".join(sorted(self.__sub_step_function_nodes))
            lines.append(
                f"    class {node_list} {DEFAULT_VISUALIZER_SUB_STEP_FUNCTION_CLASS}"
            )

        return "\n".join(lines) + "\n"

    def render_step_function(
        self,
        *,
        file_path: Optional[str] = None,
        file_name: Optional[str] = None,
        direction: str = DEFAULT_VISUALIZER_DIRECTION,
    ) -> None:
        """Writes the Mermaid flowchart definition to a .mmd file."""

        current_dir = getcwd()

        resolved_file_path = file_path or f"{current_dir}/{DEFAULT_VISUALIZER_FOLDER}"
        resolved_file_name = (
            file_name or f"{self.graph_name}.{DEFAULT_VISUALIZER_EXTENSION}"
        )

        self.__output_file_path = resolved_file_path
        self.__output_file_name = resolved_file_name

        makedirs(resolved_file_path, exist_ok=True)

        output_file = f"{resolved_file_path}/{resolved_file_name}"
        with open(
            output_file, "w", encoding=DEFAULT_VISUALIZER_STRING_ENCODING
        ) as handle:
            handle.write(self.__build_mermaid(direction))

    def render_step_function_to_string(
        self, *, direction: str = DEFAULT_VISUALIZER_DIRECTION
    ) -> str:
        """Renders the Mermaid flowchart definition as a string."""

        return self.__build_mermaid(direction)

    @property
    def output_file_name(self):
        """Returns the output file name."""
        return self.__output_file_name

    @property
    def output_file_path(self):
        """Returns the output file path."""
        return self.__output_file_path
