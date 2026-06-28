from pathlib import Path

import pytest

from src.dagbuilder import build_dag, execution_order
from src.executor import run_workflow
from src.registry import Context, StepRegistry, WorkflowSpec
from tests.conftest import (
    CallTracker,
    register_caller,
    register_eval,
    register_failure,
)


@pytest.fixture
def pipeline_tasks():
    tracker = CallTracker()

    register_caller("load", lambda ctx: {"items": [1, 2, 3], "seed": ctx.data["seed"]})
    register_caller(
        "transform",
        lambda ctx: {
            "total": sum(ctx.data["load"]["items"]),
            "seed": ctx.data["load"]["seed"],
        },
    )
    register_eval(
        "validate_transform",
        lambda _ctx, result: isinstance(result, dict) and result.get("total", 0) > 0,
    )
    register_failure(
        "log_failure",
        lambda ctx, exc: ctx.data.update({"failed": type(exc).__name__}),
    )
    return tracker


def test_full_pipeline_from_yaml(tmp_path: Path, pipeline_tasks):
    workflow = tmp_path / "pipeline.yaml"
    workflow.write_text("""
name: pipeline
steps:
  - step_name: load
    caller: load
    depends_on: []
  - step_name: transform
    caller: transform
    eval: validate_transform
    on_failure: log_failure
    depends_on: [load]
""")

    registry = StepRegistry()
    registry.load_workflow(WorkflowSpec.load(workflow))
    g = build_dag(registry.all())

    ctx = run_workflow(g, Context(data={"seed": 99}))

    assert execution_order(g) == ["load", "transform"]
    assert ctx.data["load"]["seed"] == 99
    assert ctx.data["transform"]["total"] == 6
    assert "failed" not in ctx.data


def test_full_pipeline_eval_failure_invokes_no_downstream(tmp_path: Path):
    register_caller("load", lambda ctx: {"items": []})
    register_caller("transform", lambda ctx: {"total": 0})
    register_eval("validate_transform", lambda _ctx, result: result.get("total", 0) > 0)

    workflow = tmp_path / "pipeline.yaml"
    workflow.write_text("""
name: pipeline
steps:
  - step_name: load
    caller: load
  - step_name: transform
    caller: transform
    eval: validate_transform
    depends_on: [load]
  - step_name: report
    caller: load
    depends_on: [transform]
""")

    registry = StepRegistry()
    registry.load_workflow(WorkflowSpec.load(workflow))
    ctx = run_workflow(build_dag(registry.all()), Context())

    assert "transform" in ctx.data
    assert "report" not in ctx.data


def test_full_pipeline_failure_handler_records_error(tmp_path: Path):
    register_caller(
        "load", lambda _ctx: (_ for _ in ()).throw(RuntimeError("load failed"))
    )
    register_failure(
        "log_failure", lambda ctx, exc: ctx.data.update({"error": str(exc)})
    )
    register_caller("transform", lambda ctx: {"done": True})

    workflow = tmp_path / "pipeline.yaml"
    workflow.write_text("""
name: pipeline
steps:
  - step_name: load
    caller: load
    on_failure: log_failure
  - step_name: transform
    caller: transform
    depends_on: [load]
""")

    registry = StepRegistry()
    registry.load_workflow(WorkflowSpec.load(workflow))
    ctx = run_workflow(build_dag(registry.all()), Context())

    assert ctx.data["error"] == "load failed"
    assert "transform" not in ctx.data
