# orchflow

**Quality gates and retry loops for Amazon Bedrock Converse.**

Call a model, run composable evals, retry with correct message threading — without hand-rolling the loop.

MIT License. See [LICENSE](LICENSE).

## Install

```bash
pip install "orchflow[aws]"
# or
uv sync --all-groups --extra aws
```

Requires Python 3.11+.

## Quick start

```python
from orchflow import Context, EvalVerdict, converse_with_evals
from orchflow import min_length, stop_not_truncated

ctx = Context(question="What is 2+2? Answer in one sentence.")
out = converse_with_evals(
    "us.anthropic.claude-sonnet-4-6",
    initial=ctx["question"],
    evals=[
        stop_not_truncated(),
        min_length(10, name="long_enough"),
    ],
    ctx=ctx,
    max_tokens=256,
)
print(out.result.text)
print(out.trace)  # per-turn verdicts and named eval failures
```

Orchflow owns retry message threading — you never wire `Turn.build()` yourself.

## Examples

```bash
export AWS_REGION=us-east-1
export ORCHFLOW_MODEL=us.anthropic.claude-sonnet-4-6

uv run orchflow run --example simple      # generic markdown summary
uv run orchflow run --example trade_memo  # PM trade memo (default)
uv run orchflow run --record drafts/latest.md   # save output as fixture
```

## Offline eval harness

Tune eval panels against saved drafts — no Bedrock calls:

```bash
uv run orchflow eval tests/fixtures/good_memo.md \
  --ctx '{"evidence_years":[2024,2026],"max_words":600,"min_words":100,"min_trades":1}'

uv run orchflow eval tests/fixtures/ --verbose
uv run orchflow eval tests/fixtures/bad_memo.md --only verdict_actionable --only structure
uv run orchflow eval tests/fixtures/ --json
```

Exit code **0** if all pass, **1** if any retry/fail.

## Eval primitives

```python
from orchflow import (
    gate,
    require_sections,
    word_count,
    matches,
    require_json,
    fail_on_filter,
    stop_not_truncated,
)

@gate("has_answer")
def eval_has_answer(ctx, result):
    if "4" not in result.text:
        ctx.feedback("state the numeric answer")
        return EvalVerdict.RETRY
    return EvalVerdict.OK

PANEL = [
    fail_on_filter(),
    stop_not_truncated(),
    require_sections("## Summary"),
    word_count(max=200),
    require_json(required_keys=["answer"]),
]
```

Retry feedback is prefixed with eval names: `verdict_actionable: Verdict must state...`

## API

| Export | Role |
|--------|------|
| `converse_with_evals()` | **Primary** — Bedrock Converse + eval loop + retry threading |
| `run_with_evals()` | Lower-level loop when you own the `call` function |
| `gate()` | Name an eval for traces and `--only` filtering |
| `Context` | Shared state; `feedback()` queues retry reasons |
| `EvalLoopResult.trace` | Per-turn verdicts, reasons, token counts |
| `record_output()` | Save drafts for offline eval iteration |

CLI: `orchflow run`, `orchflow eval`.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHFLOW_MODEL` | `us.anthropic.claude-sonnet-4-6` | Inference profile model ID |
| `ORCHFLOW_VISIBLE_TURNS` | `true` | tqdm progress and retry reasons |
| `ORCHFLOW_PRINT_LAST_DRAFT` | `true` | Print last draft on max turns |

## Tests

```bash
uv run pytest
uv run black --check .
```

## PyPI

```bash
uv build
uv publish   # when ready
```

See [docs/LAUNCH.md](docs/LAUNCH.md) for a launch post draft.
