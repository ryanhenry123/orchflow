# orchflow cookbook

Copy-paste recipes for common Bedrock output gates.

- Base install (`pip install orchflow`): offline panels and `orchflow eval` — no AWS credentials.
- Live Bedrock loops: `pip install "orchflow[aws]"` plus configured credentials.
- Retry progress bars: opt in with `ORCHFLOW_VISIBLE_TURNS=1` (and `ORCHFLOW_PRINT_LAST_DRAFT=1` for stderr dumps).

## 1. JSON extraction

```python
from pydantic import BaseModel
from orchflow import Context, converse_with_evals, json_object

class Answer(BaseModel):
    answer: int
    confidence: str

ctx = Context(question="What is 2+2? Reply as JSON only.")
out = converse_with_evals(
    "us.anthropic.claude-sonnet-4-6",
    initial=f"{ctx['question']} Schema: answer (int), confidence (str).",
    evals=json_object(schema=Answer),
    ctx=ctx,
    max_tokens=256,
)
```

Offline tune:

```bash
orchflow eval drafts/answer.json --panel myapp.evals:JSON_PANEL
```

## 2. Markdown sections

```python
from orchflow import Context, converse_with_evals, markdown_sections

out = converse_with_evals(
    MODEL,
    initial="Summarize vol selling risk in markdown.",
    evals=markdown_sections("## Summary", "## Risks", max_words=300),
    ctx=Context(),
)
```

## 3. No preamble

```python
from orchflow import no_preamble, markdown_sections

evals = [*markdown_sections("## Summary"), no_preamble()]
```

## 4. Markdown table (CSV-style gate)

```python
from orchflow import csv_table, markdown_sections

evals = [
    *markdown_sections("## Data"),
    csv_table(min_rows=3, min_cols=3),
]
```

## 5. Record live → tune offline

```bash
orchflow run --example trade_memo \
  --record drafts/latest.md \
  --trace runs/latest.json

orchflow eval drafts/latest.md --verbose
# fix eval → re-run eval until green → commit fixture
```

## 6. CI fixture gate

```yaml
- run: |
    orchflow eval tests/fixtures/trade_memo/ \
      --ctx '{"evidence_years":[2024,2026],"max_words":600,"min_words":100,"min_trades":1}' \
      --report eval-report.json
```

## 7. Prompt caching on retries

The initial user prompt is identical every turn. Enable Bedrock prompt cache:

```python
out = converse_with_evals(
    MODEL,
    initial=long_prompt,
    evals=panel,
    cache_initial=True,  # cachePoint after initial message
)
```

CLI: `orchflow run --cache-initial`

Check `trace[].cache_read_input_tokens` in `--trace` JSON on turn 2+.

## 8. Model A/B on your panel

```bash
orchflow compare \
  us.anthropic.claude-sonnet-4-6 \
  us.amazon.nova-pro-v1:0 \
  --example simple \
  --trace-dir runs/compare/
```

```python
from orchflow import compare_models

rows = compare_models(
    ["us.anthropic.claude-sonnet-4-6", "us.amazon.nova-pro-v1:0"],
    initial=prompt,
    evals=panel,
    max_tokens=512,
)
for row in rows:
    print(row.model_id, row.passed, row.turns, row.tokens)
```

## 9. Custom eval with named trace

```python
from orchflow import Context, EvalVerdict, gate

@gate("must_mention_vix")
def eval_vix(ctx, result):
    if "VIX" not in result.text:
        ctx.feedback("mention VIX by name")
        return EvalVerdict.RETRY
    return EvalVerdict.OK
```

Retry output: `must_mention_vix: mention VIX by name`

Filter offline: `orchflow eval draft.md --only must_mention_vix`
