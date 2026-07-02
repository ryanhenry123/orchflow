# bedrockflow

**CI for Bedrock outputs** — composable gates, correct retries, offline fixtures.

MIT License. See [LICENSE](LICENSE).

## Install

```bash
# Offline eval panels and fixture CI (no AWS credentials)
pip install bedrockflow

# Live Bedrock Converse retry loops
pip install "bedrockflow[aws]"
```

Python 3.11+.

## Quick start (offline)

Works with the base install — no boto3 required:

```python
from bedrockflow import Context, markdown_sections, run_panel
from bedrockflow.evals.offline import eval_text
from bedrockflow.evals.verdict import EvalVerdict

evals = markdown_sections("## Summary", "## Risks", max_words=300)
verdict, reasons = eval_text("## Summary\n...\n\n## Risks\n...", evals)
assert verdict is EvalVerdict.OK
```

```bash
bedrockflow eval tests/fixtures/simple/good.md \
  --panel bedrockflow.examples.simple_evals:SIMPLE_EVALS
```

> **`--panel` loads arbitrary Python** (`module.path:ATTRIBUTE`). Only point it at modules you trust.

## Quick start (Bedrock)

Requires `pip install "bedrockflow[aws]"` and configured AWS credentials:

```python
from bedrockflow import Context, converse_with_evals, markdown_sections

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
bedrockflow eval tests/fixtures/simple/ --panel bedrockflow.examples.simple_evals:SIMPLE_EVALS
bedrockflow eval draft.md --only structure --json

# Live Bedrock (requires [aws])
bedrockflow run --example simple
bedrockflow run --example trade_memo --record drafts/latest.md --trace runs/latest.json
bedrockflow run --example trade_memo --cache-initial

# Model A/B on the same panel
bedrockflow compare us.anthropic.claude-sonnet-4-6 us.amazon.nova-pro-v1:0 --example simple

# Security scanning
bedrockflow trivy
bedrockflow trivy --docker
bedrockflow bandit
```

Demo eval panels live under `bedrockflow.examples` (trade memo, simple summary). They ship for reference but are not required for library use.

## Starter panels

```python
from bedrockflow import markdown_sections, json_object, no_preamble, csv_table
```

## Progress output (opt-in)

Retry progress bars and last-draft stderr dumps are off by default:

```bash
export BEDROCKFLOW_VISIBLE_TURNS=1
export BEDROCKFLOW_PRINT_LAST_DRAFT=1
```

## Trace artifacts

`bedrockflow run --trace runs/latest.json` writes turns, named eval steps, token totals (including cache read/write).

## CI

Fixture eval runs on every PR — see [.github/workflows/ci.yml](.github/workflows/ci.yml).

```bash
uv run pytest
uv run black --check .
```

## PyPI

See [docs/LAUNCH.md](docs/LAUNCH.md) and [CHANGELOG.md](CHANGELOG.md).

Releases publish via GitHub Actions on version tags (trusted publishing — no tokens in secrets):

```bash
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin v0.3.0
```
