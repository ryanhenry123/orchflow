from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from src.models.roles import Role
from src.registerfuncs import REGISTRY, register
from src.registry import Context, Step, StepSpec


@pytest.fixture
def ctx() -> Context:
    return Context(data={"seed": 0})


@pytest.fixture(autouse=True)
def clear_registry():
    REGISTRY.clear()
    yield
    REGISTRY.clear()


def register_caller(
    name: str, func: Callable[[Context], object]
) -> Callable[..., object]:
    return register(name, Role.CALLER)(func)


def register_eval(
    name: str, func: Callable[[Context, object], bool]
) -> Callable[..., object]:
    return register(name, Role.EVAL)(func)


def register_failure(
    name: str, func: Callable[[Context, Exception], object]
) -> Callable[..., object]:
    return register(name, Role.FAILURE)(func)


def make_step(
    name: str,
    caller: Callable[[Context], object],
    *,
    depends_on: list[str] | None = None,
    eval_func: Callable[[Context, object], bool] | None = None,
    failure_func: Callable[[Context, Exception], object] | None = None,
) -> Step:
    return Step(
        step_name=name,
        caller_func=caller,
        depends_on=depends_on or [],
        eval_func=eval_func,
        failure_func=failure_func,
    )


def spec(
    step_name: str,
    caller: str,
    *,
    eval_name: str | None = None,
    on_failure: str | None = None,
    depends_on: list[str] | None = None,
) -> StepSpec:
    return StepSpec(
        step_name=step_name,
        caller=caller,
        eval=eval_name,
        on_failure=on_failure,
        depends_on=depends_on or [],
    )


class CallTracker:
    """Records step invocation order and arguments for behavioral assertions."""

    def __init__(self) -> None:
        self.events: list[tuple[str, Any]] = []

    def caller(self, name: str) -> Callable[[Context], str]:
        def _run(ctx: Context) -> str:
            self.events.append(("caller", name))
            return name

        return _run

    def eval_pass(self, name: str) -> Callable[[Context, object], bool]:
        def _run(ctx: Context, result: object) -> bool:
            self.events.append(("eval", name, result))
            return True

        return _run

    def eval_fail(self, name: str) -> Callable[[Context, object], bool]:
        def _run(ctx: Context, result: object) -> bool:
            self.events.append(("eval", name, result))
            return False

        return _run

    def failure(self, name: str) -> Callable[[Context, Exception], None]:
        def _run(ctx: Context, exc: Exception) -> None:
            self.events.append(("failure", name, type(exc).__name__, str(exc)))
            ctx.data[f"{name}_handled"] = True

        return _run


@pytest.fixture
def example_tasks():
    """Reload example task registrations after registry autouse clear."""
    import importlib
    import sys

    if "examples.tasks" not in sys.modules:
        import examples.tasks  # noqa: F401

    REGISTRY.clear()
    importlib.reload(sys.modules["examples.tasks"])
    yield sys.modules["examples.tasks"]
