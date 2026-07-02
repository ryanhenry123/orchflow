from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Turn:
    """One step in an eval retry loop (provider-agnostic state)."""

    turn: int
    assistant_drafts: list[str]
    feedback: list[str]

    @property
    def is_retry(self) -> bool:
        return self.turn > 1
