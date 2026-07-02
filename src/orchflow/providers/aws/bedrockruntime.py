from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, ConfigDict, Field

from orchflow.providers.aws.messages import (
    ConversationRole,
    assistant_message,
    cache_point,
    cached_user_message,
    system_block,
    text_block,
    user_message,
)

if TYPE_CHECKING:
    from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

_API = ConfigDict(frozen=True, populate_by_name=True)
CLIENT: BedrockRuntimeClient | None = None


def get_client(
    *, read_timeout: int = 300, connect_timeout: int = 10, max_attempts: int = 3
) -> BedrockRuntimeClient:
    global CLIENT
    if CLIENT is None:
        try:
            from boto3 import client
            from botocore.config import Config
        except ImportError as e:
            raise ImportError(
                "AWS support requires boto3. Install with: pip install orchflow[aws]"
            ) from e
        CLIENT = client(
            "bedrock-runtime",
            config=Config(
                read_timeout=read_timeout,
                connect_timeout=connect_timeout,
                retries={"max_attempts": max_attempts},
            ),
        )
    return CLIENT


class StopReason(StrEnum):
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USE = "tool_use"
    CONTENT_FILTERED = "content_filtered"
    GUARDRAIL_INTERVENED = "guardrail_intervened"
    MODEL_CONTEXT_WINDOW_EXCEEDED = "model_context_window_exceeded"


class _ApiModel(BaseModel):
    model_config = _API

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Self:
        return cls.model_validate(raw)


class TokenUsage(_ApiModel):
    input_tokens: int = Field(alias="inputTokens")
    output_tokens: int = Field(alias="outputTokens")
    total_tokens: int = Field(alias="totalTokens")
    cache_read_input_tokens: int | None = Field(
        default=None, alias="cacheReadInputTokens"
    )
    cache_write_input_tokens: int | None = Field(
        default=None, alias="cacheWriteInputTokens"
    )


class ConverseMetrics(_ApiModel):
    latency_ms: int = Field(alias="latencyMs")


class ToolUse(_ApiModel):
    tool_use_id: str = Field(alias="toolUseId")
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    type: str | None = None


class InferenceConfig(_ApiModel):
    max_tokens: int | None = Field(default=None, alias="maxTokens", ge=1)
    temperature: float | None = Field(default=None, ge=0.0)
    top_p: float | None = Field(default=None, alias="topP", ge=0.0, le=1.0)
    stop_sequences: list[str] | None = Field(default=None, alias="stopSequences")

    def to_api(self) -> dict[str, Any]:
        m = {
            "maxTokens": self.max_tokens,
            "temperature": self.temperature,
            "topP": self.top_p,
            "stopSequences": self.stop_sequences,
        }
        return {k: v for k, v in m.items() if v is not None}


class ConverseResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str
    stop_reason: StopReason | str
    usage: TokenUsage
    metrics: ConverseMetrics | None = None
    tool_uses: tuple[ToolUse, ...] = ()
    reasoning_text: str | None = None
    role: ConversationRole | str = ConversationRole.ASSISTANT
    raw: dict[str, Any] = Field(repr=False, default_factory=dict)


def parse_converse_response(response: dict[str, Any]) -> ConverseResult:
    message = response.get("output", {}).get("message", {})
    content = message.get("content", [])
    if (usage_raw := response.get("usage")) is None:
        raise ValueError("Bedrock converse response missing usage block")
    raw_stop = response.get("stopReason")
    try:
        stop = StopReason(raw_stop) if raw_stop else ""
    except ValueError:
        stop = raw_stop or ""
    return ConverseResult(
        text="".join(b["text"] for b in content if b.get("text")),
        stop_reason=stop,
        usage=TokenUsage.from_api(usage_raw),
        metrics=ConverseMetrics.from_api(m) if (m := response.get("metrics")) else None,
        tool_uses=tuple(
            ToolUse.from_api(b["toolUse"]) for b in content if b.get("toolUse")
        ),
        reasoning_text="".join(
            t
            for b in content
            if (r := b.get("reasoningContent"))
            and (t := r.get("reasoningText", {}).get("text"))
        )
        or None,
        role=message.get("role", ConversationRole.ASSISTANT),
        raw=response,
    )


def converse(
    model_id: str,
    messages: list[dict[str, Any]],
    *,
    system: str | list[dict[str, Any]] | None = None,
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
    client: BedrockRuntimeClient | None = None,
    **kwargs: Any,
) -> ConverseResult:
    """Wrap ``BedrockRuntime.Client.converse``; returns parsed ``ConverseResult``."""
    api: dict[str, Any] = {"modelId": model_id, "messages": messages}
    if system is not None:
        api["system"] = [text_block(system)] if isinstance(system, str) else system
    cfg = inference_config or InferenceConfig(
        maxTokens=max_tokens,
        temperature=temperature,
        topP=top_p,
        stopSequences=stop_sequences,
    )
    if p := cfg.to_api():
        api["inferenceConfig"] = p
    for k, v in (
        ("toolConfig", tool_config),
        ("guardrailConfig", guardrail_config),
        ("additionalModelRequestFields", additional_model_request_fields),
        ("promptVariables", prompt_variables),
        ("additionalModelResponseFieldPaths", additional_model_response_field_paths),
        ("requestMetadata", request_metadata),
        ("performanceConfig", performance_config),
        ("serviceTier", service_tier),
        ("outputConfig", output_config),
    ):
        if v is not None:
            api[k] = v
    api.update(kwargs)
    return parse_converse_response((client or get_client()).converse(**api))
