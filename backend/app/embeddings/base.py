from typing import Literal, Protocol

EmbeddingTask = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]


class EmbeddingProvider(Protocol):
    async def embed_texts(
        self,
        texts: list[str],
        *,
        task: EmbeddingTask = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]: ...
