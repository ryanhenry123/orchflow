from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from examples._runner import WORKFLOWS_DIR, execute
from examples.run_python import DAILY_REPORT
from src.dagbuilder import build_dag, execution_order
from src.registry import Context, StepRegistry, WorkflowSpec

EXPECTED_ORDER = ["load_symbol", "fetch_prices", "summarize", "format_report"]
EXPECTED_REPORT = "MSFT: avg=410.88 over 4 ticks"
EXAMPLE_CTX = Context(data={"symbol": "MSFT"})


def _load_yaml_spec() -> WorkflowSpec:
    return WorkflowSpec.load(WORKFLOWS_DIR / "daily_report.yaml")


def _load_json_spec() -> WorkflowSpec:
    payload = json.loads((WORKFLOWS_DIR / "daily_report.json").read_text())
    return WorkflowSpec.model_validate(payload)


def assert_daily_report_result(ctx: Context) -> None:
    assert ctx.data["load_symbol"] == "MSFT"
    assert ctx.data["symbol"] == "MSFT"
    assert ctx.data["fetch_prices"] == [410.5, 412.0, 409.25, 411.75]
    assert ctx.data["summarize"] == {"count": 4, "avg": 410.875}
    assert ctx.data["format_report"] == EXPECTED_REPORT
    assert "fetch_error" not in ctx.data


@pytest.mark.parametrize(
    ("name", "load_spec"),
    [
        ("python", lambda: DAILY_REPORT),
        ("yaml", _load_yaml_spec),
        ("json", _load_json_spec),
    ],
)
def test_daily_report_executes(
    example_tasks, name: str, load_spec: Callable[[], WorkflowSpec]
):
    spec = load_spec()
    assert spec.name == "daily_report"

    registry = StepRegistry()
    registry.load_workflow(spec)
    graph = build_dag(registry.all())
    assert execution_order(graph) == EXPECTED_ORDER

    ctx = execute(spec, EXAMPLE_CTX)
    assert_daily_report_result(ctx)


def test_yaml_and_json_match_python_spec(example_tasks):
    yaml_spec = _load_yaml_spec()
    json_spec = _load_json_spec()

    assert yaml_spec.model_dump() == json_spec.model_dump()
    assert yaml_spec.model_dump() == DAILY_REPORT.model_dump()


def test_run_python_main(example_tasks, capsys):
    from examples.run_python import main

    main()
    captured = capsys.readouterr().out
    assert "workflow='daily_report'" in captured
    assert f"report={EXPECTED_REPORT!r}" in captured
    assert (
        "order=['load_symbol', 'fetch_prices', 'summarize', 'format_report']"
        in captured
    )


def test_run_yaml_main(example_tasks, capsys):
    from examples.run_yaml import main

    main()
    captured = capsys.readouterr().out
    assert "workflow='daily_report'" in captured
    assert f"report={EXPECTED_REPORT!r}" in captured


def test_run_json_main(example_tasks, capsys):
    from examples.run_json import main

    main()
    captured = capsys.readouterr().out
    assert "workflow='daily_report'" in captured
    assert f"report={EXPECTED_REPORT!r}" in captured


def test_unknown_symbol_triggers_failure_handler(example_tasks):
    spec = _load_yaml_spec()
    ctx = execute(spec, Context(data={"symbol": "UNKNOWN"}))

    assert ctx.data["load_symbol"] == "UNKNOWN"
    assert "fetch_error" in ctx.data
    assert "No price feed" in ctx.data["fetch_error"]
    assert "summarize" not in ctx.data
    assert "format_report" not in ctx.data
