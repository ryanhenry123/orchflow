import re

from orchflow.evals.checks import fail_on_filter, stop_not_truncated, word_count
from orchflow.evals.names import gate
from orchflow.evals.types import EvalResult
from orchflow.evals.verdict import EvalVerdict

REQUIRED_SECTIONS = (
    "## Verdict",
    "## Trades",
    "## Triggers",
    "## Thesis",
    "## Invalidation",
)

SECTION_SPEC: dict[str, str] = {
    "## Verdict": "one line stance + desk action",
    "## Trades": "numbered; bps NAV or % with max loss/premium",
    "## Triggers": "markdown table: Signal | Level | Action (2+ data rows)",
    "## Thesis": "max 3 bullets tied to evidence years",
    "## Invalidation": "2-3 concrete falsifiers",
}


def _text(result: EvalResult) -> str:
    return result.text.strip()


def _words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _section(text: str, heading: str) -> str:
    if heading not in text:
        return ""
    block = text.split(heading, 1)[1]
    nxt = re.search(r"\n## ", block)
    return block[: nxt.start()] if nxt else block


def _table_data_rows(block: str) -> int:
    rows = [ln.strip() for ln in block.splitlines() if ln.strip().startswith("|")]
    non_sep = [r for r in rows if not re.match(r"^\|[\s\-:|]+\|$", r)]
    return max(0, len(non_sep) - 1)


DESK_ACTION_RE = re.compile(
    r"\b(?:hedge|reduce|trim|cut|add|initiate|watch|avoid|hold|flat|exit|scale)"
    r"(?:s|ed|ing)?\b",
    re.I,
)


@gate("structure")
def eval_structure(_ctx, result: EvalResult) -> EvalVerdict:
    text = _text(result)
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    if missing:
        _ctx.feedback(f"add sections: {', '.join(missing)}")
        return EvalVerdict.RETRY
    return EvalVerdict.OK


@gate("verdict_actionable")
def eval_verdict_actionable(ctx, result: EvalResult) -> EvalVerdict:
    block = _section(_text(result), "## Verdict")
    if not DESK_ACTION_RE.search(block):
        ctx.feedback(
            "Verdict must state a clear desk action (hedge/reduce/add/watch/etc.)"
        )
        return EvalVerdict.RETRY
    return EvalVerdict.OK


@gate("sized_trades")
def eval_sized_trades(ctx, result: EvalResult) -> EvalVerdict:
    block = _section(_text(result), "## Trades")
    if not re.search(
        r"\d+\s*bps|\bbps\b|basis points|%(\s+of)?\s*NAV|max (loss|premium)",
        block,
        re.I,
    ):
        ctx.feedback("size at least one leg in bps NAV or % with max loss/premium")
        return EvalVerdict.RETRY
    trades = re.findall(r"^\d+\.", block, re.MULTILINE)
    if len(trades) < ctx.get("min_trades", 1):
        ctx.feedback(f"list at least {ctx.get('min_trades', 1)} numbered trade")
        return EvalVerdict.RETRY
    return EvalVerdict.OK


@gate("triggers")
def eval_triggers(ctx, result: EvalResult) -> EvalVerdict:
    block = _section(_text(result), "## Triggers")
    if _table_data_rows(block) < 2:
        ctx.feedback("table with Signal | Level | Action and at least 2 data rows")
        return EvalVerdict.RETRY
    if not re.search(r"action", block, re.I):
        ctx.feedback("trigger table must include an Action column")
        return EvalVerdict.RETRY
    return EvalVerdict.OK


@gate("recency")
def eval_recency(ctx, result: EvalResult) -> EvalVerdict:
    start, end = ctx.get("evidence_years", (2024, 2026))
    if not re.search(
        rf"\b({'|'.join(str(y) for y in range(start, end + 1))})\b", _text(result)
    ):
        ctx.feedback(f"anchor to {start}-{end} data or events")
        return EvalVerdict.RETRY
    return EvalVerdict.OK


@gate("invalidation")
def eval_invalidation(ctx, result: EvalResult) -> EvalVerdict:
    block = _section(_text(result), "## Invalidation")
    if _words(block) < 15:
        ctx.feedback("2-3 concrete falsifiers (what proves us wrong)")
        return EvalVerdict.RETRY
    return EvalVerdict.OK


def _brevity(ctx, result: EvalResult) -> EvalVerdict:
    return word_count(
        min=ctx.get("min_words", 100),
        max=ctx.get("max_words", 600),
        name="brevity",
    )(ctx, result)


DRAFT_EVALS = [
    fail_on_filter(),
    stop_not_truncated(
        "output truncated; shorten prose but keep all 5 sections complete",
        name="not_truncated",
    ),
    eval_structure,
    eval_verdict_actionable,
    eval_sized_trades,
    eval_triggers,
    _brevity,
    eval_recency,
    eval_invalidation,
]
