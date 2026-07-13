from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str


class LLMProvider(Protocol):
    def stream_answer(self, messages: Sequence[LLMMessage]) -> AsyncIterator[str]: ...
