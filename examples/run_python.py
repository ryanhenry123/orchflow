"""Build and run the daily_report workflow entirely in Python."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples._runner import execute
from src.registry import Context, StepSpec, WorkflowSpec

DAILY_REPORT = WorkflowSpec(
    name="daily_report",
    steps=[
        StepSpec(step_name="load_symbol", caller="load_symbol"),
        StepSpec(
            step_name="fetch_prices",
            caller="fetch_prices",
            eval="validate_prices",
            on_failure="log_fetch_failure",
            depends_on=["load_symbol"],
        ),
        StepSpec(
            step_name="summarize",
            caller="summarize",
            depends_on=["fetch_prices"],
        ),
        StepSpec(
            step_name="format_report",
            caller="format_report",
            depends_on=["summarize"],
        ),
    ],
)


def main() -> None:
    execute(DAILY_REPORT, Context(data={"symbol": "MSFT"}))


if __name__ == "__main__":
    main()
