from pathlib import Path

from orchflow import converse_with_evals
from orchflow.evals.context import Context
from orchflow.evals.record import record_output
from orchflow.evals.runwithevals import MaxTurnsExceeded
from orchflow.examples.evals import DRAFT_EVALS
from orchflow.examples.prompts import SYSTEM, draft_prompt
from orchflow.examples.models import MODEL


def draft_trade_memo(ctx: Context):
    brief = ctx["brief"]
    return converse_with_evals(
        ctx.get("model_id", MODEL),
        initial=lambda c: draft_prompt({**c, **brief}),
        evals=DRAFT_EVALS,
        ctx=ctx,
        system=SYSTEM,
        max_tokens=1500,
        temperature=0.2,
        max_turns=5,
        name="trade_memo",
    )


def load_brief(ctx: Context) -> dict:
    return {
        "topic": ctx.get(
            "topic",
            "Systematic vol selling crowding and tail risk (2024-2026)",
        ),
        "horizon": ctx.get("horizon", "3-6 months"),
        "model_id": ctx.get("model_id", MODEL),
    }


def main(*, record: Path | None = None) -> None:
    ctx = Context(
        topic="Systematic vol selling crowding and tail risk (2024-2026)",
        evidence_years=(2024, 2026),
        max_words=600,
        min_words=100,
        min_trades=1,
    )
    ctx["brief"] = load_brief(ctx)
    try:
        out = draft_trade_memo(ctx)
    except MaxTurnsExceeded as exc:
        if record and exc.result.text:
            record_output(record, exc.result.text)
        raise SystemExit(1) from None
    print(out.result.text)
    print(
        f"\n--- {out.turns} turn(s), {out.result.usage.output_tokens} output tokens ---"
    )
    if out.trace:
        for step in out.trace:
            if step.reasons:
                print(
                    f"  turn {step.turn}: {step.verdict.value} — {'; '.join(step.reasons)}"
                )
    if record:
        path = record_output(record, out.result.text)
        print(f"recorded → {path}")


if __name__ == "__main__":
    main()
