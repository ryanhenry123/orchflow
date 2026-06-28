from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from modelprovider.runtime.types import (
    ConverseMetrics,
    ConverseResult,
    ConversationRole,
    StopReason,
    StreamChunk,
    StreamResult,
    TokenCountResult,
    TokenUsage,
    ToolUse,
)


def _parse_stop_reason(raw: str | None) -> StopReason | str | None:
    if raw is None:
        return None
    try:
        return StopReason(raw)
    except ValueError:
        return raw


def _extract_text(content_blocks: Iterable[dict[str, Any]]) -> str:
    return "".join(block["text"] for block in content_blocks if block.get("text"))


def _extract_reasoning(content_blocks: Iterable[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in content_blocks:
        reasoning = block.get("reasoningContent")
        if not reasoning:
            continue
        text = reasoning.get("reasoningText", {}).get("text")
        if text:
            parts.append(text)
    return "".join(parts)


def _extract_tool_uses(content_blocks: Iterable[dict[str, Any]]) -> tuple[ToolUse, ...]:
    return tuple(
        ToolUse.from_api(block["toolUse"])
        for block in content_blocks
        if block.get("toolUse")
    )


def parse_converse_response(response: dict[str, Any]) -> ConverseResult:
    output = response.get("output", {})
    message = output.get("message", {})
    content = message.get("content", [])
    usage_raw = response.get("usage")
    if usage_raw is None:
        raise ValueError("Bedrock converse response missing usage block")

    metrics_raw = response.get("metrics")
    return ConverseResult(
        text=_extract_text(content),
        stop_reason=_parse_stop_reason(response.get("stopReason")) or "",
        usage=TokenUsage.from_api(usage_raw),
        metrics=ConverseMetrics.from_api(metrics_raw) if metrics_raw else None,
        tool_uses=_extract_tool_uses(content),
        reasoning_text=_extract_reasoning(content) or None,
        role=message.get("role", ConversationRole.ASSISTANT),
        raw=response,
    )


def parse_count_tokens_response(response: dict[str, Any]) -> TokenCountResult:
    return TokenCountResult.from_api(response)


def _stream_event_name(event: dict[str, Any]) -> str:
    return next(iter(event))


def _parse_stream_chunk(event: dict[str, Any]) -> StreamChunk:
    name = _stream_event_name(event)
    payload = event[name]

    if name == "contentBlockDelta":
        delta = payload.get("delta", {})
        return StreamChunk(
            event=name,
            text_delta=delta.get("text", ""),
            reasoning_delta=delta.get("reasoningContent", {})
            .get("reasoningText", {})
            .get("text", ""),
            tool_input_delta=delta.get("toolUse", {}).get("input", ""),
            raw=event,
        )

    if name == "messageStop":
        return StreamChunk(
            event=name,
            stop_reason=_parse_stop_reason(payload.get("stopReason")),
            raw=event,
        )

    if name == "metadata":
        usage_raw = payload.get("usage")
        metrics_raw = payload.get("metrics")
        return StreamChunk(
            event=name,
            usage=TokenUsage.from_api(usage_raw) if usage_raw else None,
            metrics=ConverseMetrics.from_api(metrics_raw) if metrics_raw else None,
            raw=event,
        )

    return StreamChunk(event=name, raw=event)


class StreamAccumulator:
    def __init__(self) -> None:
        self._text: list[str] = []
        self._reasoning: list[str] = []
        self._chunks: list[StreamChunk] = []
        self._stop_reason: StopReason | str | None = None
        self._usage: TokenUsage | None = None
        self._metrics: ConverseMetrics | None = None

    def feed(self, event: dict[str, Any]) -> StreamChunk:
        chunk = _parse_stream_chunk(event)
        self._chunks.append(chunk)
        if chunk.text_delta:
            self._text.append(chunk.text_delta)
        if chunk.reasoning_delta:
            self._reasoning.append(chunk.reasoning_delta)
        if chunk.stop_reason is not None:
            self._stop_reason = chunk.stop_reason
        if chunk.usage is not None:
            self._usage = chunk.usage
        if chunk.metrics is not None:
            self._metrics = chunk.metrics
        return chunk

    def extend(self, events: Iterable[dict[str, Any]]) -> Iterator[StreamChunk]:
        for event in events:
            yield self.feed(event)

    def result(self) -> StreamResult:
        reasoning = "".join(self._reasoning)
        return StreamResult(
            text="".join(self._text),
            stop_reason=self._stop_reason,
            usage=self._usage,
            metrics=self._metrics,
            chunks=tuple(self._chunks),
            reasoning_text=reasoning or None,
        )


def collect_stream(events: Iterable[dict[str, Any]]) -> StreamResult:
    accumulator = StreamAccumulator()
    for event in events:
        accumulator.feed(event)
    return accumulator.result()
