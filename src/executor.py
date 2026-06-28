import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

import networkx as nx
from utils.log import get_logger
from src.dagbuilder import ready_steps
from src.registry import Context, Step

LOGGER = get_logger(__file__)

StepPhase = Literal[
    "start",
    "complete",
    "eval_pass",
    "eval_fail",
    "failure_handled",
    "error",
]
StepListener = Callable[..., None]
BatchListener = Callable[[int, list[str], Literal["start", "end"]], None]


@dataclass(frozen=True, slots=True)
class _StepOutcome:
    name: str
    status: Literal["completed", "eval_fail", "failure_handled", "error"]
    error: Exception | None = None
    eval_passed: bool = False


def _default_workers(batch_size: int) -> int:
    cpu = os.cpu_count() or 4
    return max(1, min(batch_size, cpu))


def _execute_step(name: str, step: Step, ctx: Context) -> _StepOutcome:
    try:
        result = step.caller_func(ctx)
        ctx.set_shared(name, result)

        if step.eval_func and not step.eval_func(ctx, result):
            return _StepOutcome(name, "eval_fail")

        return _StepOutcome(name, "completed", eval_passed=bool(step.eval_func))
    except Exception as exc:
        if step.failure_func:
            step.failure_func(ctx, exc)
            return _StepOutcome(name, "failure_handled", error=exc)
        LOGGER.error("Step %s failed with no failure handler", name)
        return _StepOutcome(name, "error", exc)


def _notify(
    on_step: StepListener | None,
    name: str,
    phase: StepPhase,
    detail: str | None = None,
) -> None:
    if on_step is not None:
        on_step(name, phase, detail)


def _apply_outcome(
    g: nx.DiGraph,
    outcome: _StepOutcome,
    completed: set[str],
    skipped: set[str],
    on_step: StepListener | None = None,
) -> None:
    if outcome.status == "completed":
        if outcome.eval_passed:
            _notify(on_step, outcome.name, "eval_pass")
        completed.add(outcome.name)
        _notify(on_step, outcome.name, "complete")
        return

    if outcome.status == "eval_fail":
        skipped.add(outcome.name)
        skipped.update(nx.descendants(g, outcome.name))
        _notify(on_step, outcome.name, "eval_fail")
        return

    if outcome.status == "failure_handled":
        skipped.add(outcome.name)
        skipped.update(nx.descendants(g, outcome.name))
        _notify(
            on_step,
            outcome.name,
            "failure_handled",
            str(outcome.error) if outcome.error else None,
        )
        return

    if outcome.error is not None:
        _notify(on_step, outcome.name, "error")
        raise outcome.error


def _run_batch_serial(
    g: nx.DiGraph,
    batch: list[str],
    ctx: Context,
    completed: set[str],
    skipped: set[str],
    on_step: StepListener | None = None,
) -> None:
    for name in batch:
        _notify(on_step, name, "start")
        step: Step = g.nodes[name]["step"]
        _apply_outcome(g, _execute_step(name, step, ctx), completed, skipped, on_step)


def _run_batch_parallel(
    g: nx.DiGraph,
    batch: list[str],
    ctx: Context,
    completed: set[str],
    skipped: set[str],
    max_workers: int,
    on_step: StepListener | None = None,
) -> None:
    for name in batch:
        _notify(on_step, name, "start")

    workers = max(1, min(max_workers, len(batch)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = pool.map(
            lambda name: _execute_step(name, g.nodes[name]["step"], ctx),
            batch,
        )
        for outcome in outcomes:
            _apply_outcome(g, outcome, completed, skipped, on_step)


def run_workflow(
    g: nx.DiGraph,
    ctx: Context,
    *,
    max_workers: int | None = None,
    on_step: StepListener | None = None,
    on_batch: BatchListener | None = None,
) -> Context:
    completed: set[str] = set()
    skipped: set[str] = set()
    wave_index = 0

    while len(completed) + len(skipped) < g.number_of_nodes():
        batch = [n for n in ready_steps(g, completed) if n not in skipped]
        if not batch:
            err = "Deadlock: no runnable steps."
            LOGGER.error(err)
            raise RuntimeError(err)

        if on_batch is not None:
            on_batch(wave_index, batch, "start")

        if len(batch) == 1 or max_workers == 1:
            _run_batch_serial(g, batch, ctx, completed, skipped, on_step)
        else:
            workers = (
                max_workers if max_workers is not None else _default_workers(len(batch))
            )
            _run_batch_parallel(g, batch, ctx, completed, skipped, workers, on_step)

        if on_batch is not None:
            on_batch(wave_index, batch, "end")
        wave_index += 1

    return ctx
