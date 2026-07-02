from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from orchflow.evals.names import eval_name
from orchflow.evals.types import EvalResult


class EvalVerdict(StrEnum):
    OK = "ok"
    RETRY = "retry"
    FAIL = "fail"


EvalFn = Callable[[Any, EvalResult], "EvalVerdict | bool | None"]


def normalize(result: EvalVerdict | bool | None) -> EvalVerdict:
    if result is None:
        return EvalVerdict.FAIL
    if isinstance(result, bool):
        return EvalVerdict.OK if result else EvalVerdict.FAIL
    return result


@dataclass(frozen=True)
class EvalStep:
    name: str
    verdict: EvalVerdict
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class PanelReport:
    verdict: EvalVerdict
    reasons: tuple[str, ...]
    steps: tuple[EvalStep, ...]


def _prefix(name: str, msg: str) -> str:
    if msg.startswith(f"{name}:"):
        return msg
    return f"{name}: {msg}"


def run_panel_report(
    evals: Sequence[EvalFn], ctx: Any, result: EvalResult
) -> PanelReport:
    reasons: list[str] = []
    steps: list[EvalStep] = []
    saw_retry = False
    for fn in evals:
        verdict = normalize(fn(ctx, result))
        step_reasons = [_prefix(eval_name(fn), msg) for msg in ctx.drain_feedback()]
        steps.append(
            EvalStep(
                name=eval_name(fn),
                verdict=verdict,
                reasons=tuple(step_reasons),
            )
        )
        if verdict is EvalVerdict.FAIL:
            return PanelReport(EvalVerdict.FAIL, tuple(reasons), tuple(steps))
        if verdict is EvalVerdict.RETRY:
            saw_retry = True
            reasons.extend(step_reasons)
    if saw_retry:
        final = reasons or ("revision requested",)
        return PanelReport(EvalVerdict.RETRY, tuple(final), tuple(steps))
    return PanelReport(EvalVerdict.OK, (), tuple(steps))


def run_panel(
    evals: Sequence[EvalFn], ctx: Any, result: EvalResult
) -> tuple[EvalVerdict, list[str]]:
    report = run_panel_report(evals, ctx, result)
    return report.verdict, list(report.reasons)
