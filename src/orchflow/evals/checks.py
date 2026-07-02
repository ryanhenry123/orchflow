from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ValidationError

from orchflow.evals.types import EvalResult
from orchflow.evals.verdict import EvalFn, EvalVerdict


def _words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _named(name: str, fn: EvalFn) -> EvalFn:
    fn.__eval_name__ = name  # type: ignore[attr-defined]
    return fn


def fail_on_filter(*, name: str = "fail_on_filter") -> EvalFn:
    def check(_ctx: Any, result: EvalResult) -> EvalVerdict:
        if result.stop_reason in ("content_filtered", "guardrail_intervened"):
            return EvalVerdict.FAIL
        return EvalVerdict.OK

    return _named(name, check)


def stop_not_truncated(
    msg: str = "output truncated; shorten and resubmit complete output",
    *,
    name: str = "stop_not_truncated",
) -> EvalFn:
    def check(ctx: Any, result: EvalResult) -> EvalVerdict:
        if result.stop_reason == "max_tokens":
            ctx.feedback(msg)
            return EvalVerdict.RETRY
        return EvalVerdict.OK

    return _named(name, check)


def require_sections(
    *headings: str,
    msg: str | None = None,
    name: str = "require_sections",
) -> EvalFn:
    def check(ctx: Any, result: EvalResult) -> EvalVerdict:
        text = result.text.strip()
        missing = [h for h in headings if h not in text]
        if missing:
            ctx.feedback(msg or f"add sections: {', '.join(missing)}")
            return EvalVerdict.RETRY
        return EvalVerdict.OK

    return _named(name, check)


def word_count(
    *,
    min: int | None = None,
    max: int | None = None,
    name: str = "word_count",
) -> EvalFn:
    def check(ctx: Any, result: EvalResult) -> EvalVerdict:
        n = _words(result.text.strip())
        if max is not None and n > max:
            ctx.feedback(f"cut to {max} words or fewer (currently {n})")
            return EvalVerdict.RETRY
        if min is not None and n < min:
            ctx.feedback(f"add detail to reach ~{min}+ words (currently {n})")
            return EvalVerdict.RETRY
        return EvalVerdict.OK

    return _named(name, check)


def min_length(
    n: int,
    *,
    msg: str | None = None,
    name: str = "min_length",
) -> EvalFn:
    def check(ctx: Any, result: EvalResult) -> EvalVerdict:
        if len(result.text.strip()) < n:
            ctx.feedback(msg or f"answer must be at least {n} characters")
            return EvalVerdict.RETRY
        return EvalVerdict.OK

    return _named(name, check)


def matches(
    pattern: str,
    *,
    msg: str | None = None,
    flags: int = 0,
    name: str = "matches",
) -> EvalFn:
    rx = re.compile(pattern, flags)

    def check(ctx: Any, result: EvalResult) -> EvalVerdict:
        if not rx.search(result.text):
            ctx.feedback(msg or f"text must match /{pattern}/")
            return EvalVerdict.RETRY
        return EvalVerdict.OK

    return _named(name, check)


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return stripped


def require_json(
    *,
    required_keys: Sequence[str] | None = None,
    schema: type[BaseModel] | None = None,
    name: str = "require_json",
) -> EvalFn:
    def check(ctx: Any, result: EvalResult) -> EvalVerdict:
        raw = _extract_json(result.text)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            ctx.feedback(f"valid JSON required: {exc.msg}")
            return EvalVerdict.RETRY
        if not isinstance(data, dict):
            ctx.feedback("JSON root must be an object")
            return EvalVerdict.RETRY
        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                ctx.feedback(f"JSON missing keys: {', '.join(missing)}")
                return EvalVerdict.RETRY
        if schema is not None:
            try:
                schema.model_validate(data)
            except ValidationError as exc:
                ctx.feedback(f"JSON schema: {exc.errors()[0]['msg']}")
                return EvalVerdict.RETRY
        return EvalVerdict.OK

    return _named(name, check)
