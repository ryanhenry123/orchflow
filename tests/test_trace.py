from orchflow.evals.context import Context
from orchflow.evals.runwithevals import run_with_evals
from orchflow.evals.verdict import EvalVerdict
from conftest import MockResult


def test_run_with_evals_records_trace():
    calls = 0

    def call(_turn):
        nonlocal calls
        calls += 1
        if calls == 1:
            return MockResult("short", output_tokens=3)
        return MockResult("long enough answer here", output_tokens=12)

    def eval_min(ctx, result):
        if len(result.text) < 10:
            ctx.feedback("too short")
            return EvalVerdict.RETRY
        return EvalVerdict.OK

    eval_min.__eval_name__ = "min_len"

    out = run_with_evals(call, [eval_min], ctx=Context(), max_turns=3)
    assert out.turns == 2
    assert len(out.trace) == 2
    assert out.trace[0].verdict is EvalVerdict.RETRY
    assert "min_len:" in out.trace[0].reasons[0]
    assert out.trace[1].verdict is EvalVerdict.OK
    assert out.trace[0].output_tokens == 3
