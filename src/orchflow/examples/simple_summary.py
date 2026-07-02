from pathlib import Path

from orchflow import converse_with_evals
from orchflow.evals.context import Context
from orchflow.evals.record import record_output
from orchflow.evals.runwithevals import MaxTurnsExceeded
from orchflow.examples.models import MODEL
from orchflow.examples.simple_evals import SIMPLE_EVALS

SYSTEM = (
    "Write concise markdown for busy readers. "
    "No preamble, no disclaimers, no filler."
)


def draft_prompt(ctx: Context) -> str:
    return (
        f"Topic: {ctx['topic']}\n\n"
        "Write a short markdown note with exactly:\n"
        "## Summary — 2-3 sentences.\n"
        "## Key Points — 3 bullet points.\n"
        f"Stay under {ctx.get('max_words', 200)} words."
    )


def run_simple_summary(ctx: Context):
    return converse_with_evals(
        ctx.get("model_id", MODEL),
        initial=lambda c: draft_prompt(c),
        evals=SIMPLE_EVALS,
        ctx=ctx,
        system=SYSTEM,
        max_tokens=512,
        temperature=0.2,
        max_turns=3,
        name="simple_summary",
    )


def main(*, record: Path | None = None) -> None:
    ctx = Context(
        topic="Why systematic vol selling builds tail risk in calm markets",
        max_words=200,
        min_words=30,
    )
    try:
        out = run_simple_summary(ctx)
    except MaxTurnsExceeded as exc:
        if record and exc.result.text:
            record_output(record, exc.result.text)
        raise SystemExit(1) from None
    print(out.result.text)
    tokens = getattr(getattr(out.result, "usage", None), "output_tokens", "?")
    print(f"\n--- {out.turns} turn(s), {tokens} output tokens ---")
    if out.trace:
        for step in out.trace:
            if step.reasons:
                print(
                    f"  turn {step.turn}: {step.verdict.value} — {'; '.join(step.reasons)}"
                )
    if record:
        path = record_output(record, out.result.text)
        print(f"recorded → {path}")
