from __future__ import annotations

from datetime import UTC, datetime
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
    history: dict[str, list[dict[str, object]]] = {}
    selected: str | None = None


class WorkflowsResponse(BaseModel):
    workflows: list[str]


def _runs_newest_first() -> list:
    runs = store.list_runs()
    for run in runs:
        if run.started_at and run.started_at.tzinfo is None:
            run.started_at = run.started_at.replace(tzinfo=UTC)
        if run.finished_at and run.finished_at.tzinfo is None:
            run.finished_at = run.finished_at.replace(tzinfo=UTC)
    runs.sort(
        key=lambda run: run.started_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    return runs


def _group_runs_by_name(runs: list) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for run in runs:
        grouped.setdefault(run.name, []).append(run)
    return grouped


def _resolve_selected_run(runs: list, selected_id: str | None):
    if not selected_id:
        return None
    return next((run for run in runs if run.workflow_id == selected_id), None)


def _visible_runs(
    runs: list, selected_id: str | None = None
) -> tuple[list, str | None]:
    grouped = _group_runs_by_name(runs)
    selected = _resolve_selected_run(runs, selected_id)
    active_selected = selected_id if selected is not None else None

    visible: list = []
    for type_runs in grouped.values():
        if selected and selected.name == type_runs[0].name:
            visible.append(selected)
        else:
            visible.append(type_runs[0])

    visible.sort(key=lambda run: run.name)
    return visible, active_selected


def _run_history(grouped: dict[str, list]) -> dict[str, list[dict[str, object]]]:
    return {
        name: [
            {
                "workflow_id": run.workflow_id,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
            }
            for run in type_runs
        ]
        for name, type_runs in sorted(grouped.items())
    }


def _serialize_run(run) -> dict[str, object]:
    return {
        "workflow_id": run.workflow_id,
        "name": run.name,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "waves": [
            {
                "index": wave.index,
                "steps": wave.steps,
                "status": wave.status,
            }
            for wave in run.waves
        ],
        "steps": [
            {
                "name": step.name,
                "caller": step.caller,
                "eval": step.eval,
                "on_failure": step.on_failure,
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


def _runs_payload(runs: list, selected_id: str | None = None) -> dict[str, object]:
    grouped = _group_runs_by_name(runs)
    visible, active_selected = _visible_runs(runs, selected_id)
    return {
        "runs": [_serialize_run(run) for run in visible],
        "history": _run_history(grouped),
        "selected": active_selected,
    }


def _pipeline_layers(steps: list) -> list[list]:
    by_name = {step.name: step for step in steps}
    depth: dict[str, int] = {}

    def step_depth(name: str, visiting: set[str] | None = None) -> int:
        if name in depth:
            return depth[name]
        visiting = visiting or set()
        if name in visiting or name not in by_name:
            return 0
        visiting.add(name)
        step = by_name[name]
        if not step.depends_on:
            value = 0
        else:
            value = (
                max(
                    step_depth(dep, visiting)
                    for dep in step.depends_on
                    if dep in by_name
                )
                + 1
            )
        depth[name] = value
        return value

    for step in steps:
        step_depth(step.name)

    if not depth:
        return []

    layers: list[list] = [[] for _ in range(max(depth.values()) + 1)]
    for step in steps:
        layers[depth[step.name]].append(step)
    return layers


@app.get("/", response_class=HTMLResponse)
def index(request: Request, run: str | None = None) -> HTMLResponse:
    runs = _runs_newest_first()
    grouped = _group_runs_by_name(runs)
    visible, selected_run_id = _visible_runs(runs, run)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "runs": runs,
            "run_pipelines": [
                {"run": item, "layers": _pipeline_layers(item.steps)}
                for item in visible
            ],
            "run_history": _run_history(grouped),
            "selected_run_id": selected_run_id,
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
def get_runs(run: str | None = None) -> RunsResponse:
    return RunsResponse(**_runs_payload(_runs_newest_first(), run))


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
