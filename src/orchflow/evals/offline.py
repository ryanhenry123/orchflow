from __future__ import annotations

import importlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from orchflow.evals.context import Context
from orchflow.evals.names import filter_evals
from orchflow.evals.types import EvalResult
from orchflow.evals.verdict import EvalFn, EvalVerdict, PanelReport, run_panel_report


@dataclass(frozen=True)
class TextResult:
    text: str
    stop_reason: str = "end_turn"


def load_panel(spec: str) -> Sequence[EvalFn]:
    """Load an eval panel from ``module.path:ATTRIBUTE``."""
    if ":" not in spec:
        raise ValueError(f"panel must be module.path:ATTRIBUTE, got {spec!r}")
    module_name, attr = spec.rsplit(":", 1)
    module = importlib.import_module(module_name)
    panel = getattr(module, attr)
    if not isinstance(panel, Sequence):
        raise TypeError(f"{spec} is not a sequence of eval functions")
    return panel


def eval_text_report(
    text: str,
    evals: Sequence[EvalFn],
    *,
    ctx: Context | dict | None = None,
    stop_reason: str = "end_turn",
) -> PanelReport:
    result: EvalResult = TextResult(text=text, stop_reason=stop_reason)
    return run_panel_report(evals, Context(ctx or {}), result)


def eval_text(
    text: str,
    evals: Sequence[EvalFn],
    *,
    ctx: Context | dict | None = None,
    stop_reason: str = "end_turn",
) -> tuple[EvalVerdict, list[str]]:
    report = eval_text_report(text, evals, ctx=ctx, stop_reason=stop_reason)
    return report.verdict, list(report.reasons)


@dataclass(frozen=True)
class FixtureReport:
    path: Path
    verdict: EvalVerdict
    reasons: list[str]
    steps: tuple[dict[str, object], ...] = ()


def eval_fixture(
    path: Path,
    evals: Sequence[EvalFn],
    *,
    ctx: Context | dict | None = None,
    stop_reason: str = "end_turn",
) -> FixtureReport:
    text = path.read_text(encoding="utf-8")
    report = eval_text_report(text, evals, ctx=ctx, stop_reason=stop_reason)
    return FixtureReport(
        path=path,
        verdict=report.verdict,
        reasons=list(report.reasons),
        steps=tuple(_step_dict(s) for s in report.steps),
    )


def _step_dict(step) -> dict[str, object]:
    return {
        "name": step.name,
        "verdict": step.verdict.value,
        "reasons": list(step.reasons),
    }


def eval_paths(
    paths: Sequence[Path],
    evals: Sequence[EvalFn],
    *,
    ctx: Context | dict | None = None,
    stop_reason: str = "end_turn",
) -> list[FixtureReport]:
    reports: list[FixtureReport] = []
    for path in paths:
        if path.is_dir():
            files = (
                sorted(path.glob("*.md"))
                + sorted(path.glob("*.txt"))
                + sorted(path.glob("*.json"))
            )
            reports.extend(
                eval_fixture(f, evals, ctx=ctx, stop_reason=stop_reason) for f in files
            )
        else:
            reports.append(eval_fixture(path, evals, ctx=ctx, stop_reason=stop_reason))
    return reports


def format_report(report: FixtureReport, *, verbose: bool = False) -> str:
    lines = [f"{report.path}: {report.verdict.value}"]
    if verbose:
        for step in report.steps:
            lines.append(f"  [{step['name']}] {step['verdict']}")
            for reason in step["reasons"]:
                lines.append(f"    - {reason}")
    else:
        for reason in report.reasons:
            lines.append(f"  - {reason}")
    return "\n".join(lines)


def reports_to_json(reports: Sequence[FixtureReport]) -> str:
    payload = [
        {
            "path": str(r.path),
            "verdict": r.verdict.value,
            "reasons": r.reasons,
            "steps": list(r.steps),
        }
        for r in reports
    ]
    return json.dumps(payload, indent=2)


def run_eval_cli(
    paths: Sequence[str | Path],
    *,
    panel: str,
    ctx: Context | dict | None = None,
    stop_reason: str = "end_turn",
    only: Sequence[str] | None = None,
    verbose: bool = False,
    as_json: bool = False,
) -> int:
    evals = filter_evals(load_panel(panel), only)
    resolved = [Path(p) for p in paths]
    reports = eval_paths(resolved, evals, ctx=ctx, stop_reason=stop_reason)
    if as_json:
        print(reports_to_json(reports))
    else:
        for report in reports:
            print(format_report(report, verbose=verbose))
    failed = any(r.verdict is not EvalVerdict.OK for r in reports)
    return 1 if failed else 0


def parse_ctx_json(raw: str | None) -> Context | None:
    if not raw:
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("ctx JSON must be an object")
    return Context(data)
