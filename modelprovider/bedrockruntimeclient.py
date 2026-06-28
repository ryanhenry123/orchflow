from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from boto3 import client
from mypy_boto3_bedrock_runtime import BedrockRuntimeClient

from modelprovider.runtime.parsing import (
    StreamAccumulator,
    collect_stream,
    parse_converse_response,
    parse_count_tokens_response,
)
from modelprovider.runtime.types import (
    ConverseRequest,
    ConverseResult,
    InferenceConfig,
    StreamChunk,
    StreamResult,
    TokenCountResult,
    system_block,
    user_message,
)
from src.models.promptmodel import PromptConfig, PromptRequest
from utils.log import get_logger

CLIENT: BedrockRuntimeClient | None = None
LOGGER = get_logger(__file__)


def _get_client(boto3_name: str = "bedrock-runtime") -> BedrockRuntimeClient:
    global CLIENT
    if CLIENT is None:
        CLIENT = client(boto3_name)
    return CLIENT


def _build_converse_api_kwargs(
    request: ConverseRequest | None = None,
    *,
    model_id: str | None = None,
    messages: list[dict[str, Any]] | None = None,
    system: list[dict[str, str]] | None = None,
    inference_config: InferenceConfig | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if request is not None:
        api_kwargs = request.to_api()
        api_kwargs.update(kwargs)
        return api_kwargs

    if model_id is None:
        raise ValueError("requires either request or model_id")

    api_kwargs: dict[str, Any] = {"modelId": model_id}
    if messages is not None:
        api_kwargs["messages"] = messages
    if system is not None:
        api_kwargs["system"] = system
    if inference_config is not None:
        inference = inference_config.to_api()
        if inference:
            api_kwargs["inferenceConfig"] = inference
    api_kwargs.update(kwargs)
    return api_kwargs


class BedrockRuntimeClass:
    """Typed facade over the Bedrock Runtime Converse, ConverseStream, and CountTokens APIs."""

    def __init__(
        self,
        boto3_name: str = "bedrock-runtime",
        *,
        client: BedrockRuntimeClient | None = None,
    ):
        self._client = client or _get_client(boto3_name)

    @property
    def raw_client(self) -> BedrockRuntimeClient:
        return self._client

    def converse(
        self,
        request: ConverseRequest | None = None,
        *,
        model_id: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        system: list[dict[str, str]] | None = None,
        inference_config: InferenceConfig | None = None,
        **kwargs: Any,
    ) -> ConverseResult:
        api_kwargs = _build_converse_api_kwargs(
            request,
            model_id=model_id,
            messages=messages,
            system=system,
            inference_config=inference_config,
            **kwargs,
        )

        LOGGER.debug("bedrock-runtime converse modelId=%s", api_kwargs.get("modelId"))
        response = self._client.converse(**api_kwargs)
        result = parse_converse_response(response)
        LOGGER.info(
            "bedrock-runtime converse modelId=%s stop=%s input_tokens=%s output_tokens=%s latency_ms=%s",
            api_kwargs.get("modelId"),
            result.stop_reason,
            result.usage.input_tokens,
            result.usage.output_tokens,
            result.metrics.latency_ms if result.metrics else None,
        )
        return result

    def _converse_stream_events(
        self,
        request: ConverseRequest | None = None,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        api_kwargs = _build_converse_api_kwargs(request, **kwargs)
        LOGGER.debug("bedrock-runtime converse_stream modelId=%s", api_kwargs.get("modelId"))
        response = self._client.converse_stream(**api_kwargs)
        yield from response["stream"]

    def converse_stream(
        self,
        request: ConverseRequest | None = None,
        *,
        model_id: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        system: list[dict[str, str]] | None = None,
        inference_config: InferenceConfig | None = None,
        **kwargs: Any,
    ) -> Iterator[StreamChunk]:
        accumulator = StreamAccumulator()
        events = self._converse_stream_events(
            request,
            model_id=model_id,
            messages=messages,
            system=system,
            inference_config=inference_config,
            **kwargs,
        )
        for event in events:
            yield accumulator.feed(event)

    def converse_stream_collect(
        self,
        request: ConverseRequest | None = None,
        **kwargs: Any,
    ) -> StreamResult:
        result = collect_stream(self._converse_stream_events(request, **kwargs))
        LOGGER.info(
            "bedrock-runtime converse_stream modelId=%s stop=%s input_tokens=%s output_tokens=%s latency_ms=%s",
            kwargs.get("model_id") or (request.model_id if request else None),
            result.stop_reason,
            result.usage.input_tokens if result.usage else None,
            result.usage.output_tokens if result.usage else None,
            result.metrics.latency_ms if result.metrics else None,
        )
        return result

    def count_tokens(
        self,
        model_id: str,
        *,
        messages: list[dict[str, Any]] | None = None,
        system: list[dict[str, str]] | None = None,
        tool_config: Mapping[str, Any] | None = None,
        additional_model_request_fields: Mapping[str, Any] | None = None,
    ) -> TokenCountResult:
        converse_input: dict[str, Any] = {}
        if messages is not None:
            converse_input["messages"] = messages
        if system is not None:
            converse_input["system"] = system
        if tool_config is not None:
            converse_input["toolConfig"] = dict(tool_config)
        if additional_model_request_fields is not None:
            converse_input["additionalModelRequestFields"] = dict(
                additional_model_request_fields
            )

        LOGGER.debug("bedrock-runtime count_tokens modelId=%s", model_id)
        response = self._client.count_tokens(
            modelId=model_id,
            input={"converse": converse_input},
        )
        result = parse_count_tokens_response(response)
        LOGGER.info(
            "bedrock-runtime count_tokens modelId=%s input_tokens=%s",
            model_id,
            result.input_tokens,
        )
        return result

    def converse_prompt(
        self,
        config: PromptConfig,
        request: PromptRequest,
        *,
        extra_messages: list[dict[str, Any]] | None = None,
    ) -> ConverseResult:
        system_text, user_text = request.render_prompt(config)
        messages = [*(extra_messages or []), user_message(user_text)]
        inference = InferenceConfig(
            maxTokens=config.max_tokens,
            temperature=config.temperature,
        )
        converse_request = ConverseRequest(
            modelId=config.model,
            system=[system_block(system_text)],
            messages=messages,
            inferenceConfig=inference,
        )
        return self.converse(converse_request)


if __name__ == "__main__":
    runtime = BedrockRuntimeClass()
    model_id = "amazon.nova-lite-v1:0"

    result = runtime.converse(
        ConverseRequest.single_turn(
            model_id,
            "Reply with exactly three words.",
            inference_config=InferenceConfig(maxTokens=16, temperature=0.0),
        )
    )
    print("converse:", result.text.strip())
    print("usage:", result.usage.model_dump())

    stream_result = runtime.converse_stream_collect(
        model_id=model_id,
        messages=[user_message("Count to 3.")],
        inference_config=InferenceConfig(maxTokens=32, temperature=0.0),
    )
    print("stream:", stream_result.text.strip())
    print("stream usage:", stream_result.usage.model_dump() if stream_result.usage else None)

    try:
        token_count = runtime.count_tokens(
            model_id,
            messages=[user_message("hello world")],
        )
        print("count_tokens:", token_count.model_dump())
    except Exception as exc:
        print("count_tokens skipped:", type(exc).__name__, str(exc))
