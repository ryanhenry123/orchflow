from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from orchflow.evals.context import Context
from orchflow.evals.runwithevals import (
    EvalFailed,
    EvalLoopResult,
    MaxTurnsExceeded,
    run_with_evals,
)
from orchflow.evals.trace_io import run_result_to_dict, token_summary, write_trace
from orchflow.evals.verdict import EvalFn
from orchflow.providers.aws.bedrockruntime import InferenceConfig, converse
from orchflow.providers.aws.messages import build_converse_messages

InitialFn = Callable[[Context], str]


def _resolve_initial(initial: str | InitialFn, ctx: Context) -> str:
    return initial(ctx) if callable(initial) else initial


def converse_with_evals(
    model_id: str,
    initial: str | InitialFn,
    evals: Sequence[EvalFn],
    *,
    ctx: Context | dict[str, Any] | None = None,
    system: str | list[dict[str, Any]] | None = None,
    max_turns: int = 3,
    name: str | None = None,
    cache_initial: bool = False,
    inference_config: InferenceConfig | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    stop_sequences: list[str] | None = None,
    tool_config: dict[str, Any] | None = None,
    guardrail_config: dict[str, Any] | None = None,
    additional_model_request_fields: dict[str, Any] | None = None,
    prompt_variables: dict[str, Any] | None = None,
    additional_model_response_field_paths: list[str] | None = None,
    request_metadata: dict[str, str] | None = None,
    performance_config: dict[str, Any] | None = None,
    service_tier: dict[str, Any] | None = None,
    output_config: dict[str, Any] | None = None,
    client: Any | None = None,
    **kwargs: Any,
) -> EvalLoopResult:
    """Call Bedrock Converse with an eval panel; owns message threading on retries."""
    ctx = Context(ctx or {})

    def call(turn):
        return converse(
            model_id,
            build_converse_messages(
                turn,
                initial=_resolve_initial(initial, ctx),
                cache_initial=cache_initial,
            ),
            system=system,
            inference_config=inference_config,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop_sequences=stop_sequences,
            tool_config=tool_config,
            guardrail_config=guardrail_config,
            additional_model_request_fields=additional_model_request_fields,
            prompt_variables=prompt_variables,
            additional_model_response_field_paths=additional_model_response_field_paths,
            request_metadata=request_metadata,
            performance_config=performance_config,
            service_tier=service_tier,
            output_config=output_config,
            client=client,
            **kwargs,
        )

    return run_with_evals(
        call,
        evals,
        ctx=ctx,
        max_turns=max_turns,
        name=name,
    )


@dataclass(frozen=True)
class ModelCompareResult:
    model_id: str
    passed: bool
    turns: int | None
    tokens: dict[str, int]
    last_reasons: tuple[str, ...]
    error: str | None = None
    text: str | None = None


def compare_models(
    model_ids: Sequence[str],
    initial: str | InitialFn,
    evals: Sequence[EvalFn],
    *,
    ctx: Context | dict[str, Any] | None = None,
    trace_dir: str | None = None,
    **kwargs: Any,
) -> list[ModelCompareResult]:
    """Run the same eval panel against multiple Bedrock models."""
    rows: list[ModelCompareResult] = []
    for model_id in model_ids:
        run_ctx = Context(ctx or {})
        try:
            out = converse_with_evals(
                model_id,
                initial,
                evals,
                ctx=run_ctx,
                **kwargs,
            )
            if trace_dir:
                write_trace(
                    f"{trace_dir.rstrip('/')}/{model_id.replace('.', '_')}.json",
                    run_result_to_dict(
                        out,
                        model_id=model_id,
                        name=kwargs.get("name"),
                        passed=True,
                    ),
                )
            rows.append(
                ModelCompareResult(
                    model_id=model_id,
                    passed=True,
                    turns=out.turns,
                    tokens=token_summary(out.trace),
                    last_reasons=(),
                    text=out.result.text,
                )
            )
        except MaxTurnsExceeded as exc:
            if trace_dir and exc.trace:
                write_trace(
                    f"{trace_dir.rstrip('/')}/{model_id.replace('.', '_')}.json",
                    {
                        **run_result_to_dict(
                            EvalLoopResult(
                                result=exc.result,
                                turns=len(exc.trace),
                                ctx=run_ctx,
                                trace=exc.trace,
                            ),
                            model_id=model_id,
                            name=kwargs.get("name"),
                            passed=False,
                            error=str(exc),
                        ),
                    },
                )
            last = exc.trace[-1].reasons if exc.trace else ()
            rows.append(
                ModelCompareResult(
                    model_id=model_id,
                    passed=False,
                    turns=len(exc.trace),
                    tokens=token_summary(exc.trace),
                    last_reasons=last,
                    error=str(exc),
                    text=exc.result.text,
                )
            )
        except EvalFailed as exc:
            rows.append(
                ModelCompareResult(
                    model_id=model_id,
                    passed=False,
                    turns=len(exc.trace) if exc.trace else None,
                    tokens=token_summary(exc.trace),
                    last_reasons=exc.trace[-1].reasons if exc.trace else (),
                    error=str(exc),
                    text=exc.result.text,
                )
            )
        except Exception as exc:
            rows.append(
                ModelCompareResult(
                    model_id=model_id,
                    passed=False,
                    turns=None,
                    tokens={
                        "output_tokens": 0,
                        "input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "cache_write_input_tokens": 0,
                    },
                    last_reasons=(),
                    error=str(exc),
                )
            )
    return rows
