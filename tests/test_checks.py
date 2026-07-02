import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from orchflow.evals.checks import (
    fail_on_filter,
    min_length,
    require_json,
    require_sections,
    stop_not_truncated,
    word_count,
)
from orchflow.evals.context import Context
from orchflow.evals.verdict import EvalVerdict, run_panel
from conftest import MockResult


def test_require_sections_passes():
    fn = require_sections("## A", "## B")
    v, reasons = run_panel([fn], Context(), MockResult("## A\nx\n## B\ny"))
    assert v is EvalVerdict.OK
    assert reasons == []


def test_require_sections_fails():
    fn = require_sections("## Missing")
    v, reasons = run_panel([fn], Context(), MockResult("nope"))
    assert v is EvalVerdict.RETRY
    assert "require_sections:" in reasons[0]


def test_word_count_max():
    fn = word_count(max=3)
    v, _ = run_panel([fn], Context(), MockResult("one two three four"))
    assert v is EvalVerdict.RETRY


def test_min_length():
    fn = min_length(20)
    v, _ = run_panel([fn], Context(), MockResult("short"))
    assert v is EvalVerdict.RETRY


def test_stop_not_truncated():
    fn = stop_not_truncated()
    v, _ = run_panel([fn], Context(), MockResult("x", stop_reason="max_tokens"))
    assert v is EvalVerdict.RETRY


def test_fail_on_filter():
    fn = fail_on_filter()
    v, _ = run_panel(
        [fn], Context(), MockResult("x", stop_reason="guardrail_intervened")
    )
    assert v is EvalVerdict.FAIL


def test_require_json_keys():
    fn = require_json(required_keys=["answer"])
    v, reasons = run_panel([fn], Context(), MockResult('{"answer": 4}'))
    assert v is EvalVerdict.OK

    v, reasons = run_panel([fn], Context(), MockResult("not json"))
    assert v is EvalVerdict.RETRY
    assert "require_json:" in reasons[0]


def test_require_json_schema():
    class M(BaseModel):
        answer: int

    fn = require_json(schema=M)
    v, _ = run_panel([fn], Context(), MockResult('{"answer": "nope"}'))
    assert v is EvalVerdict.RETRY


def test_require_json_strips_fences():
    fn = require_json(required_keys=["answer"])
    text = '```json\n{"answer": 4}\n```'
    v, _ = run_panel([fn], Context(), MockResult(text))
    assert v is EvalVerdict.OK


def test_record_output(tmp_path: Path):
    from orchflow.evals.record import record_output

    path = record_output(tmp_path / "out" / "draft.md", "hello")
    assert path.read_text() == "hello"
