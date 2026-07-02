"""Bedrock-native eval loop: call a model, run quality gates, retry with feedback."""

from orchflow.evals.checks import (
    fail_on_filter,
    matches,
    min_length,
    require_json,
    require_sections,
    stop_not_truncated,
    word_count,
)
from orchflow.evals.context import Context
from orchflow.evals.names import eval_name, filter_evals, gate
from orchflow.evals.record import record_output
from orchflow.evals.runwithevals import (
    EvalFailed,
    EvalLoopResult,
    MaxTurnsExceeded,
    TurnTrace,
    run_with_evals,
)
from orchflow.evals.turn import Turn
from orchflow.evals.types import EvalResult
from orchflow.evals.verdict import EvalFn, EvalStep, EvalVerdict, PanelReport, run_panel


def converse_with_evals(*args, **kwargs):
    from orchflow.providers.aws.converse_with_evals import converse_with_evals as impl

    return impl(*args, **kwargs)


__all__ = [
    "Context",
    "EvalFailed",
    "EvalFn",
    "EvalLoopResult",
    "EvalResult",
    "EvalStep",
    "EvalVerdict",
    "MaxTurnsExceeded",
    "PanelReport",
    "Turn",
    "TurnTrace",
    "converse_with_evals",
    "eval_name",
    "fail_on_filter",
    "filter_evals",
    "gate",
    "matches",
    "min_length",
    "record_output",
    "require_json",
    "require_sections",
    "run_panel",
    "run_with_evals",
    "stop_not_truncated",
    "word_count",
]
