from __future__ import annotations

from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field


class ConversationRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class StopReason(StrEnum):
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    TOOL_USE = "tool_use"
    CONTENT_FILTERED = "content_filtered"
    GUARDRAIL_INTERVENED = "guardrail_intervened"
    MODEL_CONTEXT_WINDOW_EXCEEDED = "model_context_window_exceeded"


def text_block(text: str) -> dict[str, str]:
    return {"text": text}


def system_block(text: str) -> dict[str, str]:
    return {"text": text}


def user_message(text: str) -> dict[str, Any]:
    return {"role": ConversationRole.USER, "content": [text_block(text)]}


def assistant_message(text: str) -> dict[str, Any]:
    return {"role": ConversationRole.ASSISTANT, "content": [text_block(text)]}


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    input_tokens: int = Field(alias="inputTokens")
    output_tokens: int = Field(alias="outputTokens")
    total_tokens: int = Field(alias="totalTokens")
    cache_read_input_tokens: int | None = Field(default=None, alias="cacheReadInputTokens")
    cache_write_input_tokens: int | None = Field(default=None, alias="cacheWriteInputTokens")

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Self:
        return cls.model_validate(raw)


class ConverseMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    latency_ms: int = Field(alias="latencyMs")

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Self:
        return cls.model_validate(raw)


class ToolUse(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    tool_use_id: str = Field(alias="toolUseId")
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    type: str | None = None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Self:
        return cls.model_validate(raw)


class InferenceConfig(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    max_tokens: int | None = Field(default=None, alias="maxTokens", ge=1)
    temperature: float | None = Field(default=None, ge=0.0)
    top_p: float | None = Field(default=None, alias="topP", ge=0.0, le=1.0)
    stop_sequences: list[str] | None = Field(default=None, alias="stopSequences")

    def to_api(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.max_tokens is not None:
            payload["maxTokens"] = self.max_tokens
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.top_p is not None:
            payload["topP"] = self.top_p
        if self.stop_sequences is not None:
            payload["stopSequences"] = self.stop_sequences
        return payload


class ConverseRequest(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    model_id: str = Field(alias="modelId")
    messages: list[dict[str, Any]] = Field(default_factory=list)
    system: list[dict[str, Any]] | None = None
    inference_config: InferenceConfig | None = Field(default=None, alias="inferenceConfig")
    tool_config: dict[str, Any] | None = Field(default=None, alias="toolConfig")
    guardrail_config: dict[str, Any] | None = Field(default=None, alias="guardrailConfig")
    additional_model_request_fields: dict[str, Any] | None = Field(
        default=None, alias="additionalModelRequestFields"
    )
    request_metadata: dict[str, str] | None = Field(default=None, alias="requestMetadata")

    def to_api(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"modelId": self.model_id}
        if self.messages:
            payload["messages"] = self.messages
        if self.system is not None:
            payload["system"] = self.system
        if self.inference_config is not None:
            inference = self.inference_config.to_api()
            if inference:
                payload["inferenceConfig"] = inference
        if self.tool_config is not None:
            payload["toolConfig"] = self.tool_config
        if self.guardrail_config is not None:
            payload["guardrailConfig"] = self.guardrail_config
        if self.additional_model_request_fields is not None:
            payload["additionalModelRequestFields"] = self.additional_model_request_fields
        if self.request_metadata is not None:
            payload["requestMetadata"] = self.request_metadata
        return payload

    @classmethod
    def single_turn(
        cls,
        model_id: str,
        user_text: str,
        *,
        system_text: str | None = None,
        inference_config: InferenceConfig | None = None,
        **kwargs: Any,
    ) -> Self:
        system = [system_block(system_text)] if system_text else None
        return cls(
            modelId=model_id,
            messages=[user_message(user_text)],
            system=system,
            inferenceConfig=inference_config,
            **kwargs,
        )


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


class StreamChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: str
    text_delta: str = ""
    reasoning_delta: str = ""
    tool_input_delta: str = ""
    stop_reason: StopReason | str | None = None
    usage: TokenUsage | None = None
    metrics: ConverseMetrics | None = None
    raw: dict[str, Any] = Field(repr=False, default_factory=dict)


class StreamResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    stop_reason: StopReason | str | None = None
    usage: TokenUsage | None = None
    metrics: ConverseMetrics | None = None
    chunks: tuple[StreamChunk, ...] = ()
    reasoning_text: str | None = None


class TokenCountResult(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    input_tokens: int = Field(alias="inputTokens")

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> Self:
        return cls.model_validate(raw)
