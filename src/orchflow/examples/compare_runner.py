from __future__ import annotations

from orchflow.evals.context import Context
from orchflow.examples.evals import DRAFT_EVALS
from orchflow.examples.prompts import (
    SYSTEM as TRADE_SYSTEM,
)
from orchflow.examples.prompts import (
    draft_prompt as trade_draft_prompt,
)
from orchflow.examples.simple_evals import SIMPLE_EVALS
from orchflow.examples.simple_summary import SYSTEM, draft_prompt
from orchflow.examples.trade_memo import load_brief
from orchflow.providers.aws.converse_with_evals import (
    ModelCompareResult,
    compare_models,
)


def compare_example(
    example: str,
    model_ids: list[str],
    *,
    trace_dir: str | None = None,
    cache_initial: bool = False,
) -> list[ModelCompareResult]:
    if example == "simple":
        return compare_models(
            model_ids,
            initial=lambda c: draft_prompt(c),
            evals=SIMPLE_EVALS,
            ctx=Context(
                topic="Why systematic vol selling builds tail risk in calm markets",
                max_words=200,
                min_words=30,
            ),
            system=SYSTEM,
            max_tokens=512,
            temperature=0.2,
            max_turns=3,
            name="simple_summary",
            trace_dir=trace_dir,
            cache_initial=cache_initial,
        )
    if example == "trade_memo":
        ctx = Context(
            topic="Systematic vol selling crowding and tail risk (2024-2026)",
            evidence_years=(2024, 2026),
            max_words=600,
            min_words=100,
            min_trades=1,
        )
        ctx["brief"] = load_brief(ctx)
        brief = ctx["brief"]
        return compare_models(
            model_ids,
            initial=lambda c: trade_draft_prompt({**c, **brief}),
            evals=DRAFT_EVALS,
            ctx=ctx,
            system=TRADE_SYSTEM,
            max_tokens=1500,
            temperature=0.2,
            max_turns=5,
            name="trade_memo",
            trace_dir=trace_dir,
            cache_initial=cache_initial,
        )
    raise ValueError(f"unknown example: {example}")


def format_compare_rows(rows: list[ModelCompareResult]) -> str:
    lines = ["model | passed | turns | output_tokens | notes"]
    lines.append("--- | --- | --- | --- | ---")
    for row in rows:
        notes = row.error or ("; ".join(row.last_reasons) if row.last_reasons else "ok")
        lines.append(
            f"{row.model_id} | {row.passed} | {row.turns} | "
            f"{row.tokens.get('output_tokens', 0)} | {notes}"
        )
    return "\n".join(lines)
