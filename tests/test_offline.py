from pathlib import Path

from orchflow.evals.context import Context
from orchflow.evals.offline import eval_fixture, eval_paths, load_panel
from orchflow.evals.verdict import EvalVerdict
from orchflow.examples.evals import DRAFT_EVALS
from orchflow.examples.simple_evals import SIMPLE_EVALS

FIXTURES = Path(__file__).parent / "fixtures"
TRADE_CTX = {
    "evidence_years": (2024, 2026),
    "max_words": 600,
    "min_words": 100,
    "min_trades": 1,
}


def test_load_panel():
    panel = load_panel("orchflow.examples.evals:DRAFT_EVALS")
    assert panel is DRAFT_EVALS


def test_good_fixture_passes():
    report = eval_fixture(
        FIXTURES / "good_memo.md",
        DRAFT_EVALS,
        ctx=TRADE_CTX,
    )
    assert report.verdict is EvalVerdict.OK
    assert report.reasons == []


def test_bad_fixture_fails_with_reasons():
    report = eval_fixture(
        FIXTURES / "bad_memo.md",
        DRAFT_EVALS,
        ctx=TRADE_CTX,
    )
    assert report.verdict is EvalVerdict.RETRY
    assert report.reasons


def test_eval_directory():
    reports = eval_paths([FIXTURES], DRAFT_EVALS, ctx=TRADE_CTX)
    names = {r.path.name for r in reports}
    assert "good_memo.md" in names
    assert "bad_memo.md" in names


def test_simple_fixture_passes():
    report = eval_fixture(FIXTURES / "simple_good.md", SIMPLE_EVALS)
    assert report.verdict is EvalVerdict.OK


def test_only_filter():
    from orchflow.evals.names import filter_evals

    filtered = filter_evals(DRAFT_EVALS, ["structure"])
    assert len(filtered) == 1
