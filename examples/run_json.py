"""Load and run the daily_report workflow from JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples._runner import WORKFLOWS_DIR, execute
from src.registry import Context, WorkflowSpec


def main() -> None:
    payload = json.loads((WORKFLOWS_DIR / "daily_report.json").read_text())
    spec = WorkflowSpec.model_validate(payload)
    execute(spec, Context(data={"symbol": "MSFT"}))


if __name__ == "__main__":
    main()
