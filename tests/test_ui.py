import time

from fastapi.testclient import TestClient

from src.ui.app import app, store
from src.ui.service import WorkflowService


def test_ui_lists_workflows():
    client = TestClient(app)
    res = client.get("/api/workflows")
    assert res.status_code == 200
    names = res.json()["workflows"]
    assert "daily_report" in names
    assert "parallel_portfolio" in names


def test_ui_index_renders_dashboard():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "Orchflow" in res.text
    assert "daily_report" in res.text
    assert "Launch" in res.text
    assert "viewport" in res.text
    assert "dashboard.js" in res.text


def test_ui_run_form_redirects():
    client = TestClient(app)
    res = client.post("/run/daily_report", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/"


def test_ui_shows_latest_run_per_workflow(example_tasks):
    store._runs.clear()
    client = TestClient(app)
    service = WorkflowService(store)
    first_id = service.start_run("daily_report")
    deadline = time.time() + 5
    while time.time() < deadline:
        run = store.get_run(first_id)
        if run and run.status != "running":
            break
        time.sleep(0.05)

    second_id = service.start_run("daily_report")
    while time.time() < deadline:
        run = store.get_run(second_id)
        if run and run.status != "running":
            break
        time.sleep(0.05)

    res = client.get("/")
    assert res.status_code == 200
    assert res.text.count("pipeline-run status-") == 1
    assert second_id[:8] in res.text
    assert f"/?run={first_id}" in res.text


def test_ui_run_query_shows_selected_run(example_tasks):
    store._runs.clear()
    client = TestClient(app)
    service = WorkflowService(store)
    first_id = service.start_run("daily_report")
    deadline = time.time() + 5
    while time.time() < deadline:
        run = store.get_run(first_id)
        if run and run.status != "running":
            break
        time.sleep(0.05)

    second_id = service.start_run("daily_report")
    while time.time() < deadline:
        run = store.get_run(second_id)
        if run and run.status != "running":
            break
        time.sleep(0.05)

    res = client.get(f"/?run={first_id}")
    assert res.status_code == 200
    assert first_id[:8] in res.text
    assert f'data-run-id="{first_id}"' in res.text


def test_api_runs_returns_history(example_tasks):
    store._runs.clear()
    client = TestClient(app)
    service = WorkflowService(store)
    first_id = service.start_run("daily_report")
    deadline = time.time() + 5
    while time.time() < deadline:
        run = store.get_run(first_id)
        if run and run.status != "running":
            break
        time.sleep(0.05)

    second_id = service.start_run("daily_report")
    while time.time() < deadline:
        run = store.get_run(second_id)
        if run and run.status != "running":
            break
        time.sleep(0.05)

    payload = client.get("/api/runs").json()
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["name"] == "daily_report"
    assert len(payload["history"]["daily_report"]) == 2
    assert payload["selected"] is None
