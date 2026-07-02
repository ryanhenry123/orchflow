from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from orchflow.evals.types import EvalResult

F = TypeVar("F", bound=Callable[..., Any])


def eval_name(fn: Callable[..., Any]) -> str:
    return str(getattr(fn, "__eval_name__", fn.__name__))


def gate(name: str | None = None) -> Callable[[F], F]:
    """Attach a stable name to an eval function for retry traces and filtering."""

    def decorator(fn: F) -> F:
        fn.__eval_name__ = name or fn.__name__  # type: ignore[attr-defined]
        return fn

    return decorator


def filter_evals(
    evals: Sequence[Callable[..., Any]], only: Sequence[str] | None
) -> list[Callable[..., Any]]:
    if not only:
        return list(evals)
    wanted = set(only)
    filtered = [fn for fn in evals if eval_name(fn) in wanted]
    if not filtered:
        raise ValueError(f"no evals matched --only {sorted(wanted)}")
    return filtered


def output_tokens(result: EvalResult) -> int | None:
    usage = getattr(result, "usage", None)
    if usage is None:
        return None
    return getattr(usage, "output_tokens", None)
