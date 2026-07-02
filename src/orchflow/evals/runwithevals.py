from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from tqdm import tqdm

from orchflow.envconfig import get_settings
from orchflow.evals.context import Context
from orchflow.evals.names import output_tokens
from orchflow.evals.turn import Turn
from orchflow.evals.types import EvalResult
from orchflow.evals.verdict import EvalFn, EvalVerdict, PanelReport, run_panel_report


def _usage_field(result: EvalResult, field: str) -> int | None:
    usage = getattr(result, "usage", None)
    if usage is None:
        return None
    return getattr(usage, field, None)


@dataclass(frozen=True)
class TurnTrace:
    turn: int
    verdict: EvalVerdict
    reasons: tuple[str, ...]
    output_tokens: int | None = None
    input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    cache_write_input_tokens: int | None = None
    steps: tuple[Any, ...] = ()


class EvalFailed(Exception):
    def __init__(self, result: EvalResult, *, trace: list[TurnTrace] | None = None):
        self.result = result
        self.trace = trace or []
        super().__init__("eval panel returned FAIL")


class MaxTurnsExceeded(Exception):
    def __init__(
        self,
        result: EvalResult,
        *,
        max_turns: int,
        trace: list[TurnTrace] | None = None,
    ):
        self.result = result
        self.max_turns = max_turns
        self.trace = trace or []
        super().__init__(f"exceeded max_turns={max_turns}")


@dataclass
class EvalLoopResult:
    result: EvalResult
    turns: int
    ctx: Context
    trace: list[TurnTrace] = field(default_factory=list)


def _trace_from_report(turn: int, report: PanelReport, result: EvalResult) -> TurnTrace:
    return TurnTrace(
        turn=turn,
        verdict=report.verdict,
        reasons=report.reasons,
        output_tokens=output_tokens(result),
        input_tokens=_usage_field(result, "input_tokens"),
        cache_read_input_tokens=_usage_field(result, "cache_read_input_tokens"),
        cache_write_input_tokens=_usage_field(result, "cache_write_input_tokens"),
        steps=report.steps,
    )


def run_with_evals(
    call: Callable[[Turn], EvalResult],
    evals: Sequence[EvalFn],
    *,
    ctx: Context | dict[str, Any] | None = None,
    max_turns: int = 3,
    name: str | None = None,
) -> EvalLoopResult:
    ctx = Context(ctx or {})
    drafts: list[str] = []
    last: EvalResult | None = None
    trace: list[TurnTrace] = []
    settings = get_settings()
    label = name or "eval loop"
    pbar = tqdm(
        range(1, max_turns + 1),
        total=max_turns,
        desc=label,
        unit="turn",
        disable=not settings.visible_turns,
    )
    for turn in pbar:
        pbar.set_postfix_str("calling model...", refresh=False)
        last = call(Turn(turn, drafts, ctx.feedback_items))
        drafts.append(last.text)
        report = run_panel_report(evals, ctx, last)
        trace.append(_trace_from_report(turn, report, last))
        pbar.set_postfix(verdict=report.verdict.value)
        if report.verdict is EvalVerdict.OK:
            return EvalLoopResult(result=last, turns=turn, ctx=ctx, trace=trace)
        if report.verdict is EvalVerdict.FAIL:
            raise EvalFailed(last, trace=trace)
        ctx.set_feedback(list(report.reasons))
        if settings.visible_turns and report.reasons:
            pbar.write("  retry: " + "; ".join(report.reasons))
        if turn == max_turns:
            if settings.print_last_draft:
                print(last.text, file=sys.stderr)
            raise MaxTurnsExceeded(last, max_turns=max_turns, trace=trace)
    raise RuntimeError("unreachable")
