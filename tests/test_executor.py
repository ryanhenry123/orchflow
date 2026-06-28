from pathlib import Path

import pytest

from src.dagbuilder import build_dag, execution_order
from src.executor import run_workflow
from src.models.roles import Role
from src.registerfuncs import register
from src.registry import Context, Step, StepRegistry, WorkflowSpec
from tests.conftest import CallTracker, make_step, register_caller, register_eval, spec


def test_empty_graph_returns_context_unchanged(ctx: Context):
    result = run_workflow(build_dag([]), ctx)
    assert result is ctx
    assert result.data == {"seed": 0}


def test_linear_execution_preserves_and_extends_context():
    def first(ctx: Context) -> int:
        ctx.data["trace"] = ["first"]
        return 1

    def second(ctx: Context) -> int:
        ctx.data["trace"].append("second")
        return ctx.data["a"] + 1

    g = build_dag(
        [
            make_step("a", first),
            make_step("b", second, depends_on=["a"]),
        ]
    )
    ctx = run_workflow(g, Context(data={"trace": []}))
    assert ctx.data["a"] == 1
    assert ctx.data["b"] == 2
    assert ctx.data["trace"] == ["first", "second"]


def test_parallel_roots_execute_in_same_batch():
    tracker = CallTracker()
    g = build_dag(
        [
            make_step("a", tracker.caller("a")),
            make_step("b", tracker.caller("b")),
            make_step("c", tracker.caller("c"), depends_on=["a", "b"]),
        ]
    )
    ctx = run_workflow(g, Context())
    assert set(tracker.events[:2]) == {("caller", "a"), ("caller", "b")}
    assert tracker.events[2] == ("caller", "c")


def test_eval_pass_allows_downstream():
    tracker = CallTracker()
    g = build_dag(
        [
            make_step(
                "a",
                tracker.caller("a"),
                eval_func=tracker.eval_pass("check_a"),
            ),
            make_step("b", tracker.caller("b"), depends_on=["a"]),
        ]
    )
    ctx = run_workflow(g, Context())
    assert ("eval", "check_a", "a") in tracker.events
    assert ("caller", "b") in tracker.events
    assert ctx.data["b"] == "b"


def test_eval_failure_skips_entire_subtree():
    tracker = CallTracker()
    g = build_dag(
        [
            make_step(
                "a",
                tracker.caller("a"),
                eval_func=tracker.eval_fail("check_a"),
            ),
            make_step("b", tracker.caller("b"), depends_on=["a"]),
            make_step("c", tracker.caller("c"), depends_on=["b"]),
        ]
    )
    ctx = run_workflow(g, Context())
    assert ("caller", "a") in tracker.events
    assert ("eval", "check_a", "a") in tracker.events
    assert ("caller", "b") not in tracker.events
    assert ("caller", "c") not in tracker.events
    assert ctx.data["a"] == "a"
    assert "b" not in ctx.data
    assert "c" not in ctx.data


def test_failure_handler_skips_downstream_only():
    tracker = CallTracker()

    def boom(_ctx: Context) -> None:
        raise RuntimeError("boom")

    g = build_dag(
        [
            make_step(
                "a",
                boom,
                failure_func=tracker.failure("handle_a"),
            ),
            make_step("b", tracker.caller("b"), depends_on=["a"]),
        ]
    )
    ctx = run_workflow(g, Context())
    assert tracker.events == [
        ("failure", "handle_a", "RuntimeError", "boom"),
    ]
    assert ctx.data["handle_a_handled"] is True
    assert "b" not in ctx.data


def test_sibling_branch_not_skipped_when_other_branch_fails():
    tracker = CallTracker()

    def boom(_ctx: Context) -> None:
        raise ValueError("left failed")

    g = build_dag(
        [
            make_step("root", tracker.caller("root")),
            make_step(
                "left",
                boom,
                depends_on=["root"],
                failure_func=tracker.failure("handle_left"),
            ),
            make_step("right", tracker.caller("right"), depends_on=["root"]),
            make_step("merge", tracker.caller("merge"), depends_on=["left", "right"]),
        ]
    )
    ctx = run_workflow(g, Context())
    assert ("caller", "root") in tracker.events
    assert ("caller", "right") in tracker.events
    assert ("failure", "handle_left", "ValueError", "left failed") in tracker.events
    assert ("caller", "merge") not in tracker.events
    assert ctx.data["right"] == "right"
    assert "merge" not in ctx.data


def test_failure_without_handler_reraises_original_error():
    def boom(_ctx: Context) -> None:
        raise RuntimeError("boom")

    g = build_dag([make_step("a", boom)])
    with pytest.raises(RuntimeError, match="boom"):
        run_workflow(g, Context())


def test_eval_receives_caller_result():
    seen: dict[str, object] = {}

    def caller(_ctx: Context) -> dict[str, int]:
        return {"value": 7}

    def check(_ctx: Context, result: object) -> bool:
        seen["result"] = result
        return True

    g = build_dag([make_step("a", caller, eval_func=check)])
    run_workflow(g, Context())
    assert seen["result"] == {"value": 7}


def test_end_to_end_from_registry_yaml_and_executor(tmp_path: Path):
    register_caller("seed", lambda ctx: ctx.data.get("seed", 0) + 1)
    register_caller("double", lambda ctx: ctx.data["seed"] * 2)
    register_eval("is_positive", lambda _ctx, result: result > 0)

    workflow = tmp_path / "workflow.yaml"
    workflow.write_text("""
name: math
steps:
  - step_name: seed
    caller: seed
    depends_on: []
  - step_name: double
    caller: double
    eval: is_positive
    depends_on: [seed]
""")

    registry = StepRegistry()
    registry.load_workflow(WorkflowSpec.load(workflow))
    g = build_dag(registry.all())
    ctx = run_workflow(g, Context(data={"seed": 3}))

    assert execution_order(g) == ["seed", "double"]
    assert ctx.data["seed"] == 4
    assert ctx.data["double"] == 8


def test_step_from_spec_rejects_role_mismatch():
    register("shared", Role.CALLER)(lambda ctx: None)

    registry = StepRegistry()
    with pytest.raises(TypeError, match="expected"):
        registry.add_spec(
            spec("step", "shared", eval_name="shared"),
        )


def test_parallel_batch_runs_concurrently():
    import threading

    barrier = threading.Barrier(2)
    started: list[str] = []

    def make(name: str, *, sync: bool = False):
        def _run(_ctx: Context) -> str:
            started.append(name)
            if sync:
                barrier.wait(timeout=1)
            return name

        return _run

    g = build_dag(
        [
            make_step("a", make("a", sync=True)),
            make_step("b", make("b", sync=True)),
            make_step("c", make("c"), depends_on=["a", "b"]),
        ]
    )
    ctx = run_workflow(g, Context(), max_workers=2)
    assert set(started[:2]) == {"a", "b"}
    assert started[2] == "c"
    assert ctx.data["c"] == "c"


def test_shared_state_merge_is_thread_safe():
    def write(symbol: str):
        def _run(ctx: Context) -> str:
            ctx.merge_shared("quotes", {symbol: symbol})
            return symbol

        return _run

    g = build_dag(
        [
            make_step("a", write("AAPL")),
            make_step("b", write("MSFT")),
            make_step(
                "c",
                lambda ctx: dict(ctx.get_shared("quotes", {})),
                depends_on=["a", "b"],
            ),
        ]
    )
    ctx = run_workflow(g, Context(data={"quotes": {}}), max_workers=2)
    assert ctx.data["quotes"] == {"AAPL": "AAPL", "MSFT": "MSFT"}


def test_on_step_listener_reports_phases():
    events: list[tuple[str, str]] = []

    def first(_ctx: Context) -> int:
        return 1

    def second(_ctx: Context) -> int:
        return 2

    def on_step(name: str, phase: str) -> None:
        events.append((name, phase))

    g = build_dag(
        [
            make_step("a", first),
            make_step("b", second, depends_on=["a"]),
        ]
    )
    run_workflow(g, Context(), on_step=on_step)
    assert ("a", "start") in events
    assert ("a", "complete") in events
    assert ("b", "start") in events
    assert ("b", "complete") in events
