from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Literal
from uuid import uuid4

StepStatus = Literal["pending", "running", "completed", "skipped", "failed"]
RunStatus = Literal["idle", "running", "completed", "failed"]
NotifyPhase = Literal["start", "complete", "skip", "error", "inherited_skip"]


@dataclass
class NotifyEvent:
    phase: NotifyPhase
    at: datetime
    detail: str | None = None

    @property
    def at_iso(self) -> str:
        return self.at.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class StepView:
    name: str
    caller: str
    depends_on: list[str]
    status: StepStatus = "pending"
    output: str | None = None
    events: list[NotifyEvent] = field(default_factory=list)


@dataclass
class WorkflowView:
    workflow_id: str
    name: str
    status: RunStatus = "idle"
    steps: list[StepView] = field(default_factory=list)
    error: str | None = None
    report: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WorkflowStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._runs: dict[str, WorkflowView] = {}

    def create_run(self, name: str, steps: list[StepView]) -> WorkflowView:
        run = WorkflowView(
            workflow_id=str(uuid4()),
            name=name,
            steps=steps,
            started_at=datetime.now(UTC),
        )
        with self._lock:
            self._runs[run.workflow_id] = run
        return run

    def list_runs(self) -> list[WorkflowView]:
        with self._lock:
            return list(self._runs.values())

    def has_active_run(self) -> bool:
        with self._lock:
            return any(run.status == "running" for run in self._runs.values())

    def get_run(self, workflow_id: str) -> WorkflowView | None:
        with self._lock:
            return self._runs.get(workflow_id)

    def set_status(self, workflow_id: str, status: RunStatus) -> None:
        with self._lock:
            run = self._require(workflow_id)
            run.status = status

    def set_step_status(
        self, workflow_id: str, step_name: str, status: StepStatus
    ) -> None:
        with self._lock:
            run = self._require(workflow_id)
            step = self._find_step(run, step_name)
            step.status = status

    def record_notify(
        self,
        workflow_id: str,
        step_name: str,
        phase: NotifyPhase,
        *,
        detail: str | None = None,
        output: str | None = None,
    ) -> None:
        with self._lock:
            run = self._require(workflow_id)
            step = self._find_step(run, step_name)
            step.events.append(
                NotifyEvent(phase=phase, at=datetime.now(UTC), detail=detail)
            )
            if output is not None:
                step.output = output

    def finish(
        self,
        workflow_id: str,
        *,
        status: RunStatus,
        report: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            run = self._require(workflow_id)
            run.status = status
            run.report = report
            run.error = error
            run.finished_at = datetime.now(UTC)

    def _find_step(self, run: WorkflowView, step_name: str) -> StepView:
        for step in run.steps:
            if step.name == step_name:
                return step
        raise KeyError(f"Unknown step: {step_name}")

    def _require(self, workflow_id: str) -> WorkflowView:
        run = self._runs.get(workflow_id)
        if run is None:
            raise KeyError(f"Unknown workflow run: {workflow_id}")
        return run
