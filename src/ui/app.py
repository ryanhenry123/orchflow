from __future__ import annotations

from datetime import UTC
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.ui.service import WorkflowService, list_workflow_names
from src.ui.store import WorkflowStore

STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

store = WorkflowStore()
service = WorkflowService(store)
templates = Jinja2Templates(directory=TEMPLATE_DIR)

app = FastAPI(title="Orchflow UI", version="0.2.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RunsResponse(BaseModel):
    runs: list[dict[str, object]]


class WorkflowsResponse(BaseModel):
    workflows: list[str]


def _runs_newest_first() -> list:
    runs = store.list_runs()
    for run in runs:
        if run.started_at and run.started_at.tzinfo is None:
            run.started_at = run.started_at.replace(tzinfo=UTC)
        if run.finished_at and run.finished_at.tzinfo is None:
            run.finished_at = run.finished_at.replace(tzinfo=UTC)
    return runs


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "runs": _runs_newest_first(),
            "workflows": list_workflow_names(),
            "auto_refresh": store.has_active_run(),
        },
    )


@app.post("/run/{name}")
def run_workflow(name: str) -> RedirectResponse:
    if name not in list_workflow_names():
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {name}")
    try:
        service.start_run(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/workflows", response_model=WorkflowsResponse)
def get_workflows() -> WorkflowsResponse:
    return WorkflowsResponse(workflows=list_workflow_names())


@app.get("/api/runs", response_model=RunsResponse)
def get_runs() -> RunsResponse:
    runs = [
        {
            "workflow_id": run.workflow_id,
            "name": run.name,
            "status": run.status,
            "steps": [
                {
                    "name": step.name,
                    "caller": step.caller,
                    "depends_on": step.depends_on,
                    "status": step.status,
                    "output": step.output,
                    "events": [
                        {
                            "phase": event.phase,
                            "at": event.at_iso,
                            "detail": event.detail,
                        }
                        for event in step.events
                    ],
                }
                for step in run.steps
            ],
            "report": run.report,
            "error": run.error,
        }
        for run in _runs_newest_first()
    ]
    return RunsResponse(runs=runs)


@app.post("/api/workflows/{name}/run")
def start_workflow_api(name: str) -> dict[str, str]:
    if name not in list_workflow_names():
        raise HTTPException(status_code=404, detail=f"Unknown workflow: {name}")
    try:
        workflow_id = service.start_run(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"workflow_id": workflow_id}
