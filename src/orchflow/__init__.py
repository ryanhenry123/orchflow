"""Bedrock-native eval loop: call a model, run quality gates, retry with feedback."""

from importlib.metadata import PackageNotFoundError, version

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
from orchflow.evals.trace_io import write_run_artifact, write_trace
from orchflow.evals.turn import Turn
from orchflow.evals.types import EvalResult
from orchflow.evals.verdict import EvalFn, EvalStep, EvalVerdict, PanelReport, run_panel
from orchflow.panels import csv_table, json_object, markdown_sections, no_preamble

try:
    __version__ = version("orchflow")
except PackageNotFoundError:
    __version__ = "0.3.0"


def converse_with_evals(*args, **kwargs):
    from orchflow.providers.aws.converse_with_evals import converse_with_evals as impl

    return impl(*args, **kwargs)


def compare_models(*args, **kwargs):
    from orchflow.providers.aws.converse_with_evals import compare_models as impl

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
    "__version__",
    "compare_models",
    "converse_with_evals",
    "csv_table",
    "eval_name",
    "fail_on_filter",
    "filter_evals",
    "gate",
    "json_object",
    "markdown_sections",
    "matches",
    "min_length",
    "no_preamble",
    "record_output",
    "require_json",
    "require_sections",
    "run_panel",
    "run_with_evals",
    "stop_not_truncated",
    "word_count",
    "write_run_artifact",
    "write_trace",
]
