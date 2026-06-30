"""Tests for the Visualizer class (Mermaid flowchart generation)."""

import pytest

from stepfunction.core.step_function.step_function import StepFunction
from stepfunction.core.visualizer.visualizer import Visualizer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def noop(x):
    return x


def user_type_router(result):
    if result.get("user_type") == "INTERNAL":
        return "InternalFlow"
    return "ExternalFlow"


def ticket_router(result):
    if result.get("ticket_key") and result.get("ticket_status") == "Active":
        return "InternalFlow"
    return "ExternalFlow"


def router_to_unknown_step(result):
    if result:
        return "DoesNotExist"
    return "ExternalFlow"


def explicit_if_else_router(value):
    if value == "XYZ":
        return "InternalFlow"
    else:
        return "ExternalFlow"


def build_visualizer(sf: StepFunction) -> Visualizer:
    return Visualizer(sf.name, sf.steps)


# ---------------------------------------------------------------------------
# Basic node / edge generation
# ---------------------------------------------------------------------------


def test_visualize_requires_steps():
    visualizer = Visualizer("Empty", None)

    with pytest.raises(ValueError):
        visualizer.visualize_step_function()


def test_plain_step_node_and_success_edge():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, next_step="StepB")
    sf.add_step("StepB", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert output.startswith("flowchart TD")
    assert 'StepA["StepA"]' in output
    assert 'StepB["StepB"]' in output
    assert 'StepA -->|"Success"| StepB' in output


def test_step_names_with_spaces_get_sanitized_node_ids():
    sf = StepFunction("Demo")
    sf.add_step("First Step", noop, next_step="Second Step")
    sf.add_step("Second Step", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert 'First_Step["First Step"]' in output
    assert 'Second_Step["Second Step"]' in output
    assert 'First_Step -->|"Success"| Second_Step' in output
    assert "First Step[" not in output


def test_node_id_collisions_are_disambiguated():
    sf = StepFunction("Demo")
    sf.add_step("First Step", noop, next_step="First_Step")
    sf.add_step("First_Step", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert 'First_Step["First Step"]' in output
    assert 'First_Step_2["First_Step"]' in output
    assert 'First_Step -->|"Success"| First_Step_2' in output


def test_on_failure_edge_is_dashed():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, on_failure="Fail")
    sf.add_step("Fail", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert 'StepA -.->|"Failure"| Fail' in output
    assert "linkStyle" not in output


def test_stop_on_failure_edge_gets_red_link_style():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, on_failure="Fail", stop_on_failure=True)
    sf.add_step("Fail", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert 'StepA -.->|"Stop on Failure"| Fail' in output
    assert "linkStyle 0 stroke:red" in output


def test_dict_branch_edges():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, branch={"yes": "StepB", "no": "StepC"})
    sf.add_step("StepB", noop)
    sf.add_step("StepC", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert 'StepA -->|"Branch: yes"| StepB' in output
    assert 'StepA -->|"Branch: no"| StepC' in output


def test_parallel_step_fan_out():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, next_step="Parallel")
    sf.add_step(
        "Parallel", {"task1": noop, "task2": noop}, parallel=True, next_step="StepB"
    )
    sf.add_step("StepB", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert 'task1["task1"]' in output
    assert "Parallel -.-> task1" in output
    assert "task1 --> StepB" in output
    assert "Parallel -.-> task2" in output
    assert "task2 --> StepB" in output


def test_sub_step_function_node_gets_distinct_shape_and_class():
    sub = StepFunction("Sub")
    sub.add_step("SubStep", noop)
    sub.set_start_step("SubStep")

    sf = StepFunction("Demo")
    sf.add_sub_step_function("SubFlow", sub, next_step="End")
    sf.add_step("End", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert 'SubFlow(["SubFlow"])' in output
    assert "classDef subStepFunction" in output
    assert "class SubFlow subStepFunction" in output


# ---------------------------------------------------------------------------
# Callable branch routers (static AST inspection)
# ---------------------------------------------------------------------------


def test_callable_branch_extracts_conditional_and_fallback_edges():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, branch=user_type_router)
    sf.add_step("InternalFlow", noop)
    sf.add_step("ExternalFlow", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert (
        "StepA -->|\"Branch: result.get('user_type') == 'INTERNAL'\"| InternalFlow"
        in output
    )
    assert 'StepA -->|"Branch: else"| ExternalFlow' in output


def test_callable_branch_handles_compound_conditions():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, branch=ticket_router)
    sf.add_step("InternalFlow", noop)
    sf.add_step("ExternalFlow", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert "Branch:" in output
    assert "InternalFlow" in output
    assert 'StepA -->|"Branch: else"| ExternalFlow' in output


def test_callable_branch_ignores_targets_not_in_known_steps():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, branch=router_to_unknown_step)
    sf.add_step("ExternalFlow", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert "DoesNotExist" not in output
    assert 'StepA -->|"Branch: else"| ExternalFlow' in output


def test_callable_branch_negates_condition_for_explicit_else():
    # An explicit if/else shares one ast.If node for both branches - without
    # tracking which side a return is on, both would get the same (un-negated)
    # condition label.
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, branch=explicit_if_else_router)
    sf.add_step("InternalFlow", noop)
    sf.add_step("ExternalFlow", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert "StepA -->|\"Branch: value == 'XYZ'\"| InternalFlow" in output
    assert "StepA -->|\"Branch: not (value == 'XYZ')\"| ExternalFlow" in output


def test_callable_branch_without_source_yields_no_edges():
    router = eval("lambda result: 'ExternalFlow'")  # no inspectable source file

    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, branch=router)
    sf.add_step("ExternalFlow", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    output = visualizer.render_step_function_to_string()

    assert "Branch" not in output


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------


def test_render_step_function_writes_mmd_file(tmp_path):
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, next_step="StepB")
    sf.add_step("StepB", noop)

    visualizer = build_visualizer(sf)
    visualizer.visualize_step_function()
    visualizer.render_step_function(file_path=str(tmp_path), file_name="demo.mmd")

    output_file = tmp_path / "demo.mmd"
    assert output_file.exists()

    content = output_file.read_text(encoding="utf-8")
    assert content.startswith("flowchart TD")
    assert visualizer.output_file_name == "demo.mmd"
    assert visualizer.output_file_path == str(tmp_path)


# ---------------------------------------------------------------------------
# StepFunction.visualize() / visualize_to_string() validation
# ---------------------------------------------------------------------------
#
# These go through StepFunction (not Visualizer directly), since the
# dangling-reference check lives in StepFunction.validate() and is invoked
# from visualize()/visualize_to_string() before handing steps to the
# Visualizer - the same check execute() already runs before running a
# workflow.


def test_visualize_to_string_raises_for_unknown_next_step():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, next_step="Typo_Step")
    sf.add_step("StepB", noop)
    sf.set_start_step("StepA")

    with pytest.raises(ValueError, match="unknown next_step"):
        sf.visualize_to_string()


def test_visualize_to_string_raises_without_start_step():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop)

    with pytest.raises(ValueError, match="No start step set"):
        sf.visualize_to_string()


def test_visualize_to_string_passes_for_valid_workflow():
    sf = StepFunction("Demo")
    sf.add_step("StepA", noop, next_step="StepB")
    sf.add_step("StepB", noop)
    sf.set_start_step("StepA")

    output = sf.visualize_to_string()

    assert 'StepA -->|"Success"| StepB' in output
