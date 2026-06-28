from __future__ import annotations

import importlib
import json
import threading
from pathlib import Path
from typing import Literal

import networkx as nx
from src.dagbuilder import build_dag
from src.executor import StepPhase, run_workflow
from src.registry import Context, StepRegistry, WorkflowSpec
from src.ui.store import StepStatus, StepView, WorkflowStore

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / "examples" / "workflows"

TASK_MODULES: dict[str, str] = {
    "daily_report": "examples.tasks",
    "parallel_portfolio": "examples.parallel_tasks",
}

DEFAULT_CONTEXT: dict[str, dict[str, object]] = {
    "daily_report": {"symbol": "MSFT"},
    "parallel_portfolio": {"symbols": ["AAPL", "MSFT"]},
}

MAX_WORKERS: dict[str, int | None] = {
    "daily_report": None,
    "parallel_portfolio": 2,
}

PHASE_LABELS: dict[StepPhase, str] = {
    "start": "started",
    "complete": "completed",
    "eval_pass": "eval passed",
    "eval_fail": "eval failed",
    "failure_handled": "failure handled",
    "error": "failed",
}

PHASE_STATUS: dict[StepPhase, StepStatus] = {
    "start": "running",
    "complete": "completed",
    "eval_pass": "running",
    "eval_fail": "eval_failed",
    "failure_handled": "handled",
    "error": "failed",
}

CASCADE_PHASES: frozenset[StepPhase] = frozenset({"eval_fail", "failure_handled"})


def list_workflow_names() -> list[str]:
    names = {path.stem for path in WORKFLOWS_DIR.glob("*.yaml")}
    return sorted(names)


def load_workflow_spec(name: str) -> WorkflowSpec:
    yaml_path = WORKFLOWS_DIR / f"{name}.yaml"
    json_path = WORKFLOWS_DIR / f"{name}.json"
    if yaml_path.exists():
        return WorkflowSpec.load(yaml_path)
    if json_path.exists():
        payload = json.loads(json_path.read_text())
        return WorkflowSpec.model_validate(payload)
    raise FileNotFoundError(f"Workflow not found: {name}")


def _step_views(spec: WorkflowSpec) -> list[StepView]:
    return [
        StepView(
            name=step.step_name,
            caller=step.caller,
            eval=step.eval,
            on_failure=step.on_failure,
            depends_on=list(step.depends_on),
        )
        for step in spec.steps
    ]


def _format_output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, indent=2, default=str)
    except TypeError:
        return repr(value)


def _report_from_context(name: str, ctx: Context) -> str | None:
    if name == "parallel_portfolio":
        value = ctx.data.get("format_portfolio_report")
    else:
        value = ctx.data.get("format_report")
    return str(value) if value is not None else None


class WorkflowService:
    def __init__(self, store: WorkflowStore) -> None:
        self.store = store

    def start_run(self, name: str) -> str:
        spec = load_workflow_spec(name)
        task_module = TASK_MODULES.get(name)
        if task_module is None:
            raise ValueError(f"No task module configured for workflow: {name}")

        run = self.store.create_run(name, _step_views(spec))
        thread = threading.Thread(
            target=self._execute,
            args=(run.workflow_id, spec, task_module),
            daemon=True,
        )
        thread.start()
        return run.workflow_id

    def _execute(self, workflow_id: str, spec: WorkflowSpec, task_module: str) -> None:
        step_meta = {step.step_name: step for step in spec.steps}

        try:
            self.store.set_status(workflow_id, "running")
            importlib.import_module(task_module)

            registry = StepRegistry()
            registry.load_workflow(spec)
            graph = build_dag(registry.all())
            ctx = Context(data=dict(DEFAULT_CONTEXT.get(spec.name, {})))

            def on_step(
                step_name: str,
                phase: StepPhase,
                error_detail: str | None = None,
            ) -> None:
                meta = step_meta.get(step_name)
                detail = PHASE_LABELS[phase]
                if phase == "eval_fail" and meta and meta.eval:
                    detail = f"eval failed ({meta.eval})"
                elif phase == "failure_handled" and meta and meta.on_failure:
                    suffix = f": {error_detail}" if error_detail else ""
                    detail = f"handled by {meta.on_failure}{suffix}"
                elif phase == "eval_pass" and meta and meta.eval:
                    detail = f"eval passed ({meta.eval})"

                output = None
                if phase == "complete":
                    output = _format_output(ctx.get_shared(step_name))

                self.store.set_step_status(workflow_id, step_name, PHASE_STATUS[phase])
                self.store.record_notify(
                    workflow_id,
                    step_name,
                    phase,
                    detail=detail,
                    output=output,
                )

                if phase in CASCADE_PHASES:
                    for downstream in nx.descendants(graph, step_name):
                        self.store.set_step_status(workflow_id, downstream, "skipped")
                        self.store.record_notify(
                            workflow_id,
                            downstream,
                            "inherited_skip",
                            detail="skipped (upstream branch did not pass)",
                        )

            def on_batch(
                wave_index: int,
                steps: list[str],
                event: Literal["start", "end"],
            ) -> None:
                self.store.record_wave(
                    workflow_id,
                    wave_index,
                    steps,
                    event=event,
                )

            ctx = run_workflow(
                graph,
                ctx,
                max_workers=MAX_WORKERS.get(spec.name),
                on_step=on_step,
                on_batch=on_batch,
            )
            self.store.finish(
                workflow_id,
                status="completed",
                report=_report_from_context(spec.name, ctx),
            )
        except Exception as exc:
            self.store.finish(workflow_id, status="failed", error=str(exc))
