from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dagbuilder import build_dag, execution_order
from src.executor import run_workflow
from src.registry import Context, StepRegistry, WorkflowSpec

WORKFLOWS_DIR = Path(__file__).resolve().parent / "workflows"


def execute(spec: WorkflowSpec, ctx: Context | None = None) -> Context:
    import examples.tasks  # noqa: F401 — register step functions

    registry = StepRegistry()
    registry.load_workflow(spec)
    graph = build_dag(registry.all())
    result = run_workflow(graph, ctx or Context())
    print(f"workflow={spec.name!r} order={execution_order(graph)}")
    print(f"report={result.data.get('format_report')!r}")
    return result
