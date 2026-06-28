from __future__ import annotations

from functools import wraps

import pytest

from src.models.roles import Role, validate_signature
from src.registry import Context


def test_validate_accepts_minimal_annotations():
    def caller(ctx):
        return ctx

    def eval_fn(ctx, result):
        return True

    def failure(ctx, exc):
        pass

    validate_signature(caller, Role.CALLER)
    validate_signature(eval_fn, Role.EVAL)
    validate_signature(failure, Role.FAILURE)


@pytest.mark.parametrize("role", list(Role))
def test_validate_accepts_typed_signatures(role: Role):
    if role is Role.CALLER:

        def fn(ctx: Context) -> dict:
            return {}

    elif role is Role.EVAL:

        def fn(ctx: Context, result: object) -> bool:
            return True

    else:

        def fn(ctx: Context, exc: Exception) -> None:
            pass

    validate_signature(fn, role)


def test_validate_unwraps_decorated_function():
    def inner(ctx: Context) -> None:
        pass

    @wraps(inner)
    def outer(ctx: Context) -> None:
        return inner(ctx)

    validate_signature(outer, Role.CALLER)


@pytest.mark.parametrize(
    ("role", "factory", "match"),
    [
        (Role.CALLER, lambda: (lambda a, b: a), "expected 1 positional"),
        (Role.EVAL, lambda: (lambda ctx: True), "expected 2 positional"),
        (Role.FAILURE, lambda: (lambda ctx: None), "expected 2 positional"),
    ],
)
def test_wrong_arity_raises(role, factory, match):
    with pytest.raises(TypeError, match=match):
        validate_signature(factory(), role)


def test_eval_rejects_non_bool_return():
    def bad(ctx: Context, result: object) -> str:
        return "nope"

    with pytest.raises(TypeError, match="return must be"):
        validate_signature(bad, Role.EVAL)


def test_eval_accepts_optional_bool_return():
    def ok(ctx: Context, result: object) -> bool | None:
        return None

    validate_signature(ok, Role.EVAL)


def test_failure_rejects_non_exception_second_param():
    def bad(ctx: Context, code: int) -> None:
        pass

    with pytest.raises(TypeError, match="second param must accept Exception"):
        validate_signature(bad, Role.FAILURE)


def _failure_exception(ctx: Context, exc: Exception) -> None:
    pass


def _failure_base(ctx: Context, exc: BaseException) -> None:
    pass


def _failure_optional(ctx: Context, exc: Exception | None) -> None:
    pass


@pytest.mark.parametrize(
    "fn",
    [_failure_exception, _failure_base, _failure_optional],
)
def test_failure_handler_signatures(fn):
    validate_signature(fn, Role.FAILURE)
