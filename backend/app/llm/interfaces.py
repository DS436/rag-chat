from dataclasses import dataclass


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    citations: list[dict[str, str]]


class EmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class LLMProvider:
    def answer(
        self,
        question: str,
        context: list[dict[str, str]],
        chat_history: list[dict[str, str]],
    ) -> GroundedAnswer:
        raise NotImplementedError
