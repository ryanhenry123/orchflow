from dataclasses import dataclass


@dataclass(frozen=True)
class MockResult:
    text: str
    stop_reason: str = "end_turn"
    output_tokens: int | None = None

    @property
    def usage(self):
        if self.output_tokens is None:
            return None

        @dataclass(frozen=True)
        class U:
            output_tokens: int

        return U(output_tokens=self.output_tokens)
