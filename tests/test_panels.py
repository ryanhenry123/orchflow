from conftest import MockResult
from orchflow.evals.context import Context
from orchflow.evals.verdict import EvalVerdict, run_panel
from orchflow.panels import csv_table, json_object, markdown_sections, no_preamble


def test_markdown_sections_panel():
    panel = markdown_sections("## Summary", max_words=50)
    good = "## Summary\n" + "word " * 20
    v, _ = run_panel(panel, Context(), MockResult(good))
    assert v is EvalVerdict.OK

    v, reasons = run_panel(panel, Context(), MockResult("no sections"))
    assert v is EvalVerdict.RETRY
    assert any("structure:" in r for r in reasons)


def test_json_object_panel():
    panel = json_object(required_keys=["answer"])
    v, _ = run_panel(panel, Context(), MockResult('{"answer": 4}'))
    assert v is EvalVerdict.OK


def test_no_preamble():
    v, _ = run_panel([no_preamble()], Context(), MockResult("## Summary\nHi"))
    assert v is EvalVerdict.OK
    v, _ = run_panel([no_preamble()], Context(), MockResult("Sure! ## Summary\nHi"))
    assert v is EvalVerdict.RETRY


def test_csv_table():
    table = """## Data
| A | B |
| --- | --- |
| 1 | 2 |
| 3 | 4 |
"""
    v, _ = run_panel([csv_table(min_rows=2)], Context(), MockResult(table))
    assert v is EvalVerdict.OK
