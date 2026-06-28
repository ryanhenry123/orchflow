import time

from fastapi.testclient import TestClient

from src.ui.app import app, store
from src.ui.service import DEFAULT_CONTEXT, WorkflowService


def test_service_records_eval_pass_and_waves(example_tasks):
    store._runs.clear()
    service = WorkflowService(store)
    workflow_id = service.start_run("daily_report")
    deadline = time.time() + 5
    while time.time() < deadline:
        run = store.get_run(workflow_id)
        if run and run.status != "running":
            break
        time.sleep(0.05)

    run = store.get_run(workflow_id)
    assert run is not None
    assert run.status == "completed"
    assert run.waves
    fetch = next(step for step in run.steps if step.name == "fetch_prices")
    phases = [event.phase for event in fetch.events]
    assert "eval_pass" in phases
    assert fetch.eval == "validate_prices"
    assert fetch.on_failure == "log_fetch_failure"


def test_api_runs_includes_eval_roles_and_waves(example_tasks):
    store._runs.clear()
    client = TestClient(app)
    client.post("/api/workflows/daily_report/run")
    deadline = time.time() + 5
    payload = {"runs": []}
    while time.time() < deadline:
        res = client.get("/api/runs")
        payload = res.json()
        if payload["runs"] and payload["runs"][0]["status"] != "running":
            break
        time.sleep(0.05)

    assert payload["runs"]
    step = payload["runs"][0]["steps"][1]
    assert step["eval"] == "validate_prices"
    assert step["on_failure"] == "log_fetch_failure"
    assert payload["runs"][0]["waves"]


def test_service_records_failure_handled_and_skips_downstream(
    example_tasks, monkeypatch
):
    store._runs.clear()
    monkeypatch.setitem(DEFAULT_CONTEXT, "daily_report", {"symbol": "UNKNOWN"})
    service = WorkflowService(store)
    workflow_id = service.start_run("daily_report")
    deadline = time.time() + 5
    while time.time() < deadline:
        run = store.get_run(workflow_id)
        if run and run.status != "running":
            break
        time.sleep(0.05)

    run = store.get_run(workflow_id)
    assert run is not None
    assert run.status == "completed"
    fetch = next(step for step in run.steps if step.name == "fetch_prices")
    phases = [event.phase for event in fetch.events]
    assert "failure_handled" in phases
    assert fetch.status == "handled"
    assert fetch.on_failure == "log_fetch_failure"
    summarize = next(step for step in run.steps if step.name == "summarize")
    assert summarize.status == "skipped"
    skip_events = [
        event for event in summarize.events if event.phase == "inherited_skip"
    ]
    assert skip_events
