from pathlib import Path

from orchflow.evals.context import Context
from orchflow.evals.runwithevals import MaxTurnsExceeded
from orchflow.examples.evals import DRAFT_EVALS
from orchflow.examples.models import MODEL
from orchflow.examples.prompts import SYSTEM, draft_prompt
from orchflow.examples.runner import finish_run, handle_run_failure
from orchflow.providers.aws.converse_with_evals import converse_with_evals


def draft_trade_memo(ctx: Context, *, cache_initial: bool = False):
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
        cache_initial=cache_initial,
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


def main(
    *,
    record: Path | None = None,
    trace: Path | None = None,
    cache_initial: bool = False,
) -> None:
    ctx = Context(
        topic="Systematic vol selling crowding and tail risk (2024-2026)",
        evidence_years=(2024, 2026),
        max_words=600,
        min_words=100,
        min_trades=1,
    )
    ctx["brief"] = load_brief(ctx)
    model_id = ctx.get("model_id", MODEL)
    try:
        out = draft_trade_memo(ctx, cache_initial=cache_initial)
    except MaxTurnsExceeded as exc:
        handle_run_failure(
            exc,
            model_id=model_id,
            name="trade_memo",
            record=record,
            trace=trace,
        )
        raise SystemExit(1) from None
    finish_run(
        out,
        model_id=model_id,
        name="trade_memo",
        record=record,
        trace=trace,
    )


if __name__ == "__main__":
    main()
