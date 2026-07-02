import json
from pathlib import Path

import pytest

from orchflow.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
TRADE_CTX = (
    '{"evidence_years":[2024,2026],"max_words":600,"min_words":100,"min_trades":1}'
)


def test_eval_cli_good_fixture(capsys):
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "eval",
                str(FIXTURES / "trade_memo" / "good_memo.md"),
                "--panel",
                "orchflow.examples.evals:DRAFT_EVALS",
                "--ctx",
                TRADE_CTX,
            ]
        )
    out = capsys.readouterr().out
    assert exc.value.code == 0
    assert "good_memo.md: ok" in out


def test_eval_cli_bad_fixture_exits_nonzero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "eval",
                str(FIXTURES / "trade_memo" / "bad_memo.md"),
                "--panel",
                "orchflow.examples.evals:DRAFT_EVALS",
            ]
        )
    out = capsys.readouterr().out
    assert exc.value.code == 1
    assert "bad_memo.md: retry" in out


def test_eval_cli_verbose(capsys):
    with pytest.raises(SystemExit):
        main(
            [
                "eval",
                str(FIXTURES / "trade_memo" / "bad_memo.md"),
                "--panel",
                "orchflow.examples.evals:DRAFT_EVALS",
                "--verbose",
                "--only",
                "structure",
            ]
        )
    out = capsys.readouterr().out
    assert "[structure]" in out


def test_eval_cli_json(capsys):
    with pytest.raises(SystemExit):
        main(
            [
                "eval",
                str(FIXTURES / "simple" / "good.md"),
                "--panel",
                "orchflow.examples.simple_evals:SIMPLE_EVALS",
                "--json",
            ]
        )
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data[0]["verdict"] == "ok"


def test_eval_report_file(tmp_path: Path):
    report = tmp_path / "report.json"
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "eval",
                str(FIXTURES / "trade_memo" / "good_memo.md"),
                "--panel",
                "orchflow.examples.evals:DRAFT_EVALS",
                "--ctx",
                TRADE_CTX,
                "--report",
                str(report),
            ]
        )
    assert exc.value.code == 0
    assert report.exists()
    data = json.loads(report.read_text())
    assert data[0]["verdict"] == "ok"


def test_cli_requires_subcommand():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
