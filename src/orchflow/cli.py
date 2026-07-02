from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXAMPLES = {
    "trade_memo": "orchflow.examples.trade_memo:main",
    "simple": "orchflow.examples.simple_summary:main",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orchflow",
        description="Bedrock eval loops, offline fixtures, and model comparison.",
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
    run_p.add_argument(
        "--trace",
        type=Path,
        default=None,
        help="Write JSON run trace (turns, evals, tokens) to this path",
    )
    run_p.add_argument(
        "--cache-initial",
        action="store_true",
        help="Bedrock prompt cache on the initial user message (retries)",
    )

    eval_p = sub.add_parser(
        "eval",
        help="Run an eval panel on fixture file(s) or directories",
    )
    eval_p.add_argument("paths", nargs="+", help="Fixture files or directories")
    eval_p.add_argument(
        "--panel",
        default="orchflow.examples.simple_evals:SIMPLE_EVALS",
        help="Eval panel as module.path:ATTRIBUTE (imports arbitrary Python — trusted use only)",
    )
    eval_p.add_argument("--ctx", default=None, help="JSON context passed to evals")
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
    eval_p.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write JSON eval report to file (implies --json to stdout if unset)",
    )

    compare_p = sub.add_parser(
        "compare",
        help="Run the same example eval panel against multiple Bedrock models",
    )
    compare_p.add_argument(
        "models",
        nargs="+",
        help="Bedrock model IDs (inference profiles)",
    )
    compare_p.add_argument(
        "--example",
        choices=sorted(EXAMPLES),
        default="simple",
        help="Example config to run (default: simple)",
    )
    compare_p.add_argument(
        "--trace-dir",
        type=Path,
        default=None,
        help="Directory for per-model JSON traces",
    )
    compare_p.add_argument(
        "--cache-initial",
        action="store_true",
        help="Bedrock prompt cache on the initial user message",
    )
    compare_p.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit JSON comparison table",
    )

    trivy_p = sub.add_parser(
        "trivy",
        help="Run Trivy vulnerability scanner (fs scan by default)",
    )
    trivy_p.add_argument(
        "trivy_args",
        nargs="*",
        help="Optional args passed to trivy (e.g. fs . --format json)",
    )
    trivy_p.add_argument(
        "--path",
        default=".",
        help="Scan path for default filesystem scan (default: .)",
    )
    trivy_p.add_argument(
        "--severity",
        default="HIGH,CRITICAL",
        help="Severities for default scan",
    )
    trivy_p.add_argument(
        "--scanners",
        default="vuln,secret,misconfig",
        help="Scanners for default scan",
    )
    trivy_p.add_argument(
        "--format",
        default="table",
        dest="trivy_format",
        help="Output format for default scan",
    )
    trivy_p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for default scan",
    )
    trivy_p.add_argument(
        "--ignore-file",
        type=Path,
        default=None,
        help="Trivy ignore file (default: .trivyignore)",
    )
    trivy_p.add_argument(
        "--exit-code",
        type=int,
        default=1,
        help="Trivy exit code when vulnerabilities found (default: 1)",
    )
    trivy_p.add_argument(
        "--docker",
        action="store_true",
        help="Run pinned aquasec/trivy image via docker instead of local binary",
    )

    bandit_p = sub.add_parser(
        "bandit",
        help="Run Bandit Python security linter (src scan by default)",
    )
    bandit_p.add_argument(
        "bandit_args",
        nargs="*",
        help="Optional args passed to bandit (e.g. -r src -f json)",
    )
    bandit_p.add_argument(
        "--path",
        default="src/orchflow",
        help="Scan path for default recursive scan (default: src/orchflow)",
    )
    bandit_p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Bandit config file (default: .github/bandit.yaml)",
    )
    bandit_p.add_argument(
        "--severity",
        choices=["low", "medium", "high"],
        default="low",
        help="Minimum severity for default scan (default: low)",
    )
    bandit_p.add_argument(
        "--format",
        default="txt",
        dest="bandit_format",
        help="Output format for default scan",
    )
    bandit_p.add_argument(
        "--exit-code",
        type=int,
        default=1,
        help="Exit code when issues found (default: 1; use 0 for --exit-zero)",
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
        from orchflow.evals.offline import parse_ctx_json, reports_to_json, run_eval_cli

        ctx = parse_ctx_json(args.ctx)
        if args.report:
            from orchflow.evals.names import filter_evals
            from orchflow.evals.offline import eval_paths, load_panel

            evals = filter_evals(load_panel(args.panel), args.only)
            reports = eval_paths(
                [Path(p) for p in args.paths],
                evals,
                ctx=ctx,
                stop_reason=args.stop_reason,
            )
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(reports_to_json(reports), encoding="utf-8")
            failed = any(r.verdict.value != "ok" for r in reports)
            raise SystemExit(1 if failed else 0)
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

    if args.command == "compare":
        from orchflow.examples.compare_runner import (
            compare_example,
            format_compare_rows,
        )

        rows = compare_example(
            args.example,
            args.models,
            trace_dir=str(args.trace_dir) if args.trace_dir else None,
            cache_initial=args.cache_initial,
        )
        if args.as_json:
            payload = [
                {
                    "model_id": r.model_id,
                    "passed": r.passed,
                    "turns": r.turns,
                    "tokens": r.tokens,
                    "last_reasons": list(r.last_reasons),
                    "error": r.error,
                }
                for r in rows
            ]
            print(json.dumps(payload, indent=2))
        else:
            print(format_compare_rows(rows))
        raise SystemExit(0 if all(r.passed for r in rows) else 1)

    if args.command == "trivy":
        from orchflow.security.trivy import TrivyNotFoundError, run_trivy

        try:
            code = run_trivy(
                args.trivy_args or None,
                path=args.path,
                severity=args.severity,
                scanners=args.scanners,
                fmt=args.trivy_format,
                output=args.output,
                ignore_file=args.ignore_file,
                exit_code=args.exit_code,
                use_docker=args.docker,
            )
        except TrivyNotFoundError as exc:
            print(exc, file=sys.stderr)
            raise SystemExit(127) from None
        raise SystemExit(code)

    if args.command == "bandit":
        from orchflow.security.bandit import BanditNotFoundError, run_bandit

        try:
            code = run_bandit(
                args.bandit_args or None,
                path=args.path,
                config=args.config,
                severity=args.severity,
                fmt=args.bandit_format,
                exit_code=args.exit_code,
            )
        except BanditNotFoundError as exc:
            print(exc, file=sys.stderr)
            raise SystemExit(127) from None
        raise SystemExit(code)

    if args.command == "run":
        run_main = _import_main(EXAMPLES[args.example])
        run_main(
            record=args.record,
            trace=args.trace,
            cache_initial=args.cache_initial,
        )
        return

    parser.print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
