from fastapi.testclient import TestClient

from src.ui.app import app


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
    assert "Run daily_report" in res.text
    assert "local-time" in res.text
    assert "Launch" in res.text


def test_ui_run_form_redirects():
    client = TestClient(app)
    res = client.post("/run/daily_report", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/"
