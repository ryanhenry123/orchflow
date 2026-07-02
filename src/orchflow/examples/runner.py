from __future__ import annotations

from pathlib import Path

from orchflow.evals.record import record_output
from orchflow.evals.runwithevals import EvalLoopResult, MaxTurnsExceeded
from orchflow.evals.trace_io import write_run_artifact


def finish_run(
    out: EvalLoopResult,
    *,
    model_id: str | None = None,
    name: str | None = None,
    record: Path | None = None,
    trace: Path | None = None,
) -> None:
    print(out.result.text)
    usage = getattr(out.result, "usage", None)
    tokens = getattr(usage, "output_tokens", "?")
    print(f"\n--- {out.turns} turn(s), {tokens} output tokens ---")
    if out.trace:
        for step in out.trace:
            if step.reasons:
                print(
                    f"  turn {step.turn}: {step.verdict.value} — "
                    f"{'; '.join(step.reasons)}"
                )
    if record:
        path = record_output(record, out.result.text)
        print(f"recorded → {path}")
    if trace:
        path = write_run_artifact(
            trace,
            out,
            model_id=model_id,
            name=name,
            passed=True,
        )
        print(f"trace → {path}")


def handle_run_failure(
    exc: MaxTurnsExceeded,
    *,
    model_id: str | None = None,
    name: str | None = None,
    record: Path | None = None,
    trace: Path | None = None,
) -> None:
    if record and exc.result.text:
        record_output(record, exc.result.text)
    if trace:
        from orchflow.evals.context import Context
        from orchflow.evals.runwithevals import EvalLoopResult

        write_run_artifact(
            trace,
            EvalLoopResult(
                result=exc.result,
                turns=len(exc.trace),
                ctx=Context(),
                trace=exc.trace,
            ),
            model_id=model_id,
            name=name,
            passed=False,
            error=str(exc),
        )
        print(f"trace → {trace}")
