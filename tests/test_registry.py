from pathlib import Path

import pytest

from src.models.roles import Role
from src.registry import Context, Step, StepRegistry, StepSpec, WorkflowSpec
from tests.conftest import register_caller, register_eval, register_failure, spec


def test_referenced_function_names_collects_all_roles():
    wf = WorkflowSpec(
        name="wf",
        steps=[
            StepSpec(
                step_name="s1",
                caller="fetch",
                eval="check",
                on_failure="alert",
            ),
            StepSpec(step_name="s2", caller="summarize"),
        ],
    )
    assert wf.referenced_function_names() == {"fetch", "check", "alert", "summarize"}


def test_referenced_function_names_omits_optional_fields():
    wf = WorkflowSpec(name="wf", steps=[StepSpec(step_name="s1", caller="fetch")])
    assert wf.referenced_function_names() == {"fetch"}


def test_duplicate_step_names_lists_offenders():
    with pytest.raises(ValueError, match="Duplicate step name"):
        WorkflowSpec(
            name="wf",
            steps=[
                StepSpec(step_name="dup", caller="a"),
                StepSpec(step_name="dup", caller="b"),
            ],
        )


def test_workflow_spec_load_from_yaml(tmp_path: Path):
    path = tmp_path / "wf.yaml"
    path.write_text("""
name: daily
steps:
  - step_name: fetch
    caller: fetch
    depends_on: []
""")
    loaded = WorkflowSpec.load(path)
    assert loaded.name == "daily"
    assert loaded.steps[0].step_name == "fetch"
    assert loaded.steps[0].caller == "fetch"


def test_workflow_spec_load_rejects_non_dict(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text("just a string\n")
    with pytest.raises(TypeError, match="Expected dict"):
        WorkflowSpec.load(path)


def test_load_workflow_reports_all_missing_functions():
    register_caller("exists", lambda ctx: None)
    wf = WorkflowSpec(
        name="wf",
        steps=[
            spec("s1", "exists"),
            spec("s2", "missing_a"),
            spec("s3", "missing_b", eval_name="missing_eval"),
        ],
    )
    registry = StepRegistry()
    with pytest.raises(ValueError, match="Unregistered task") as exc:
        registry.load_workflow(wf)
    message = str(exc.value)
    assert "missing_a" in message
    assert "missing_b" in message
    assert "missing_eval" in message


def test_load_workflow_rejects_unknown_dependency():
    register_caller("fetch", lambda ctx: None)
    registry = StepRegistry()
    with pytest.raises(ValueError, match="depends on unknown steps"):
        registry.load_workflow(
            WorkflowSpec(
                name="wf",
                steps=[spec("s1", "fetch", depends_on=["ghost"])],
            )
        )


def test_load_workflow_resolves_all_roles():
    def caller(ctx: Context) -> dict:
        return {"ok": True}

    def check(_ctx: Context, result: object) -> bool:
        return isinstance(result, dict)

    def alert(_ctx: Context, exc: Exception) -> None:
        pass

    register_caller("fetch", caller)
    register_eval("check_fetch", check)
    register_failure("alert", alert)

    registry = StepRegistry()
    registry.load_workflow(
        WorkflowSpec(
            name="wf",
            steps=[
                spec(
                    "fetch",
                    "fetch",
                    eval_name="check_fetch",
                    on_failure="alert",
                )
            ],
        )
    )
    step = registry.get("fetch")
    assert step.caller_func is caller
    assert step.eval_func is check
    assert step.failure_func is alert


def test_step_registry_duplicate_step_raises():
    register_caller("fetch", lambda ctx: None)
    registry = StepRegistry()
    registry.load_workflow(
        WorkflowSpec(name="wf", steps=[spec("fetch", "fetch")]),
    )
    with pytest.raises(ValueError, match="Duplicate step"):
        registry.add(
            Step(
                step_name="fetch",
                caller_func=lambda ctx: None,
            )
        )


def test_step_registry_get_unknown_raises():
    with pytest.raises(KeyError, match="Unknown step: missing"):
        StepRegistry().get("missing")


def test_load_workflow_multi_step_dependencies():
    order: list[str] = []

    def record(name: str):
        def _run(_ctx: Context) -> None:
            order.append(name)

        return _run

    register_caller("a", record("a"))
    register_caller("b", record("b"))
    register_caller("c", record("c"))

    registry = StepRegistry()
    registry.load_workflow(
        WorkflowSpec(
            name="wf",
            steps=[
                spec("a", "a"),
                spec("b", "b", depends_on=["a"]),
                spec("c", "c", depends_on=["b"]),
            ],
        )
    )
    assert {s.step_name for s in registry.all()} == {"a", "b", "c"}
    assert registry.get("c").depends_on == ["b"]
