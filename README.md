# orchflow

**CI for Bedrock outputs** — composable gates, correct retries, offline fixtures.

MIT License. See [LICENSE](LICENSE).

## Install

```bash
# Offline eval panels and fixture CI (no AWS credentials)
pip install orchflow

# Live Bedrock Converse retry loops
pip install "orchflow[aws]"
```

Python 3.11+.

## Quick start (offline)

Works with the base install — no boto3 required:

```python
from orchflow import Context, markdown_sections, run_panel
from orchflow.evals.offline import eval_text
from orchflow.evals.verdict import EvalVerdict

evals = markdown_sections("## Summary", "## Risks", max_words=300)
verdict, reasons = eval_text("## Summary\n...\n\n## Risks\n...", evals)
assert verdict is EvalVerdict.OK
```

```bash
orchflow eval tests/fixtures/simple/good.md \
  --panel orchflow.examples.simple_evals:SIMPLE_EVALS
```

> **`--panel` loads arbitrary Python** (`module.path:ATTRIBUTE`). Only point it at modules you trust.

## Quick start (Bedrock)

Requires `pip install "orchflow[aws]"` and configured AWS credentials:

```python
from orchflow import Context, converse_with_evals, markdown_sections

out = converse_with_evals(
    "us.anthropic.claude-sonnet-4-6",
    initial="Summarize tail risk in vol selling.",
    evals=markdown_sections("## Summary", "## Risks", max_words=300),
    ctx=Context(),
    max_tokens=512,
)
print(out.trace)  # per-turn named eval failures + tokens
```

See [docs/COOKBOOK.md](docs/COOKBOOK.md) for JSON gates, tables, model compare, prompt caching.

## CLI

```bash
# Offline fixture CI (no AWS)
orchflow eval tests/fixtures/simple/ --panel orchflow.examples.simple_evals:SIMPLE_EVALS
orchflow eval draft.md --only structure --json

# Live Bedrock (requires [aws])
orchflow run --example simple
orchflow run --example trade_memo --record drafts/latest.md --trace runs/latest.json
orchflow run --example trade_memo --cache-initial

# Model A/B on the same panel
orchflow compare us.anthropic.claude-sonnet-4-6 us.amazon.nova-pro-v1:0 --example simple

# Security scanning
orchflow trivy
orchflow trivy --docker
orchflow bandit
```

Demo eval panels live under `orchflow.examples` (trade memo, simple summary). They ship for reference but are not required for library use.

## Starter panels

```python
from orchflow import markdown_sections, json_object, no_preamble, csv_table
```

## Progress output (opt-in)

Retry progress bars and last-draft stderr dumps are off by default:

```bash
export ORCHFLOW_VISIBLE_TURNS=1
export ORCHFLOW_PRINT_LAST_DRAFT=1
```

## Trace artifacts

`orchflow run --trace runs/latest.json` writes turns, named eval steps, token totals (including cache read/write).

## CI

Fixture eval runs on every PR — see [.github/workflows/ci.yml](.github/workflows/ci.yml).

```bash
uv run pytest
uv run black --check .
```

## PyPI

See [docs/LAUNCH.md](docs/LAUNCH.md) and [CHANGELOG.md](CHANGELOG.md).

```bash
uv build && uv publish
```
