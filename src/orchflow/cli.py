from __future__ import annotations

import argparse
from pathlib import Path

EXAMPLES = {
    "trade_memo": "orchflow.examples.trade_memo:main",
    "simple": "orchflow.examples.simple_summary:main",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchflow",
        description="Bedrock eval loops and offline eval panels.",
    )
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run a Bedrock example with eval panel")
    run_p.add_argument(
        "--example",
        choices=sorted(EXAMPLES),
        default="trade_memo",
        help="Which example to run (default: trade_memo)",
    )
    run_p.add_argument(
        "--record",
        type=Path,
        default=None,
        help="Save final draft to this path (also saved on max turns)",
    )

    eval_p = sub.add_parser(
        "eval",
        help="Run an eval panel on fixture file(s) or directories (*.md, *.txt)",
    )
    eval_p.add_argument(
        "paths",
        nargs="+",
        help="Fixture files or directories",
    )
    eval_p.add_argument(
        "--panel",
        default="orchflow.examples.evals:DRAFT_EVALS",
        help="Eval panel as module.path:ATTRIBUTE",
    )
    eval_p.add_argument(
        "--ctx",
        default=None,
        help="JSON context passed to evals",
    )
    eval_p.add_argument(
        "--stop-reason",
        default="end_turn",
        help="Simulated stop reason (default: end_turn)",
    )
    eval_p.add_argument(
        "--only",
        action="append",
        default=None,
        metavar="NAME",
        help="Run only eval(s) with this name (repeatable)",
    )
    eval_p.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-eval verdicts and reasons",
    )
    eval_p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit JSON report",
    )

    return parser


def _import_main(spec: str):
    import importlib

    module_name, attr = spec.rsplit(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "eval":
        from orchflow.evals.offline import parse_ctx_json, run_eval_cli

        ctx = parse_ctx_json(args.ctx)
        code = run_eval_cli(
            args.paths,
            panel=args.panel,
            ctx=ctx,
            stop_reason=args.stop_reason,
            only=args.only,
            verbose=args.verbose,
            as_json=args.as_json,
        )
        raise SystemExit(code)

    if args.command == "run" or args.command is None:
        example = getattr(args, "example", "trade_memo")
        record = getattr(args, "record", None)
        run_main = _import_main(EXAMPLES[example])
        run_main(record=record)
        return

    parser.print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
