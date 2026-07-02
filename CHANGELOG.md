# Changelog

All notable changes to this project are documented here.

## [0.3.0] - 2026-07-01

### Added

- Composable eval panels with `OK` / `RETRY` / `FAIL` verdicts and named gate traces.
- `converse_with_evals` and `compare_models` for Amazon Bedrock Converse retry loops.
- Offline fixture runner: `orchflow eval` for markdown/JSON CI without AWS credentials.
- Starter panels: `markdown_sections`, `json_object`, `no_preamble`, `csv_table`.
- JSON run traces with per-turn token totals (including prompt cache read/write).
- `orchflow trivy` helper for local/container vulnerability scans.
- `orchflow bandit` helper for Python SAST (Bandit) on `src/orchflow`.

### Fixed

- Base `pip install orchflow` (no extras) imports and runs offline eval without boto3.
- CLI requires an explicit subcommand (`run`, `eval`, `compare`, `trivy`, `bandit`).
- Progress bars and last-draft stderr output are opt-in via `ORCHFLOW_VISIBLE_TURNS=1` and `ORCHFLOW_PRINT_LAST_DRAFT=1`.

### Packaging

- PEP 561 marker (`py.typed`) and `orchflow.__version__`.
- Generated Bedrock catalog and dev shell scripts excluded from published wheels.
