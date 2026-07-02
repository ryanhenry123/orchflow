from conftest import MockResult
from orchflow.evals.context import Context
from orchflow.evals.runwithevals import run_with_evals
from orchflow.evals.trace_io import run_result_to_dict, write_run_artifact
from orchflow.evals.verdict import EvalVerdict


def test_trace_json_roundtrip(tmp_path):
    def call(_turn):
        return MockResult("hello world long enough", output_tokens=5)

    def ok(_ctx, _result):
        return EvalVerdict.OK

    ok.__eval_name__ = "ok"
    out = run_with_evals(call, [ok], ctx=Context(), max_turns=2)
    payload = run_result_to_dict(out, model_id="test-model", name="demo")
    assert payload["passed"] is True
    assert payload["tokens"]["output_tokens"] == 5
    assert payload["trace"][0]["verdict"] == "ok"

    path = write_run_artifact(tmp_path / "run.json", out, model_id="m", name="n")
    assert path.exists()
    assert '"turns": 1' in path.read_text()


def test_turn_trace_includes_token_fields():
    def call(turn):
        if turn.turn == 1:
            return MockResult(
                "short",
                output_tokens=5,
                input_tokens=100,
            )
        return MockResult(
            "long enough answer here",
            output_tokens=10,
            input_tokens=100,
            cache_read_input_tokens=50,
        )

    def fail_first(ctx, result):
        if len(result.text) < 20:
            ctx.feedback("short")
            return EvalVerdict.RETRY
        return EvalVerdict.OK

    fail_first.__eval_name__ = "len"
    out = run_with_evals(call, [fail_first], max_turns=3)
    assert len(out.trace) == 2
    assert out.trace[1].cache_read_input_tokens == 50
