"""Bedrock Converse message helpers (no boto3/botocore imports)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from orchflow.evals.turn import Turn


class ConversationRole(StrEnum):
    USER, ASSISTANT = "user", "assistant"


def text_block(text: str) -> dict[str, str]:
    return {"text": text}


def cache_point() -> dict[str, dict[str, str]]:
    return {"cachePoint": {"type": "default"}}


system_block = text_block


def user_message(text: str) -> dict[str, Any]:
    return {
        "role": ConversationRole.USER,
        "content": [text_block(text)],
    }


def cached_user_message(text: str) -> dict[str, Any]:
    """User message with a Bedrock prompt-cache breakpoint after ``text``."""
    return {
        "role": ConversationRole.USER,
        "content": [text_block(text), cache_point()],
    }


def assistant_message(text: str) -> dict[str, Any]:
    return {
        "role": ConversationRole.ASSISTANT,
        "content": [text_block(text)],
    }


def _initial_user(initial: str, *, cache_initial: bool) -> dict[str, Any]:
    if cache_initial:
        return cached_user_message(initial)
    return user_message(initial)


def build_converse_messages(
    turn: Turn,
    *,
    initial: str,
    cache_initial: bool = False,
    revision_heading: str = "Revise your full memo (all sections). Address:",
) -> list[dict[str, Any]]:
    """Build Bedrock Converse ``messages`` for one eval-loop turn."""
    if not turn.is_retry:
        return [_initial_user(initial, cache_initial=cache_initial)]
    msgs = [
        _initial_user(initial, cache_initial=cache_initial),
        assistant_message(turn.assistant_drafts[-1]),
    ]
    msgs.append(user_message(f"{revision_heading}\n- " + "\n- ".join(turn.feedback)))
    return msgs
