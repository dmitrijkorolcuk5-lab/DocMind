import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import DependencyUnavailableError
from app.embeddings.gemini import GeminiEmbeddingProvider


class RecordingGeminiClient:
    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions
        self.requests: list[dict[str, object]] = []

    async def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> httpx.Response:
        del url, headers
        self.requests.append(json)
        requests = json["requests"]
        assert isinstance(requests, list)
        return httpx.Response(
            200,
            json={
                "embeddings": [
                    {"values": [1.0 for _ in range(self.dimensions)]}
                    for _ in requests
                ]
            },
            request=httpx.Request("POST", "https://example.test"),
        )


@pytest.fixture
def gemini_settings() -> Settings:
    return Settings(
        GEMINI_API_KEY="test-key",
        EMBEDDING_PROVIDER="gemini",
        EMBEDDING_MODEL="gemini-embedding-001",
        EMBEDDING_DIMENSIONS=768,
        EMBEDDING_BATCH_SIZE=2,
    )


async def test_document_embedding_request_uses_task_and_output_dimensionality(
    gemini_settings: Settings,
) -> None:
    provider = GeminiEmbeddingProvider(gemini_settings)
    client = RecordingGeminiClient(dimensions=768)

    embeddings = await provider._try_embed_batch(
        client, ["first document", "second document"], "RETRIEVAL_DOCUMENT"
    )

    assert len(embeddings) == 2
    [request] = client.requests
    requests = request["requests"]
    assert isinstance(requests, list)
    assert all(item["taskType"] == "RETRIEVAL_DOCUMENT" for item in requests)
    assert all(item["outputDimensionality"] == 768 for item in requests)
    assert all("embedContentConfig" not in item for item in requests)


async def test_query_embedding_request_uses_query_task_and_output_dimensionality(
    gemini_settings: Settings,
) -> None:
    provider = GeminiEmbeddingProvider(gemini_settings)
    client = RecordingGeminiClient(dimensions=768)

    embeddings = await provider._try_embed_batch(client, ["search query"], "RETRIEVAL_QUERY")

    assert len(embeddings) == 1
    [request] = client.requests
    requests = request["requests"]
    assert isinstance(requests, list)
    [item] = requests
    assert item["taskType"] == "RETRIEVAL_QUERY"
    assert item["outputDimensionality"] == 768


async def test_returned_768_dimensional_embeddings_pass_validation(
    gemini_settings: Settings,
) -> None:
    provider = GeminiEmbeddingProvider(gemini_settings)
    client = RecordingGeminiClient(dimensions=768)

    embeddings = await provider._try_embed_batch(client, ["content"], "RETRIEVAL_DOCUMENT")

    assert len(embeddings[0]) == 768


async def test_unexpected_3072_dimensional_response_fails_clearly(
    gemini_settings: Settings,
) -> None:
    provider = GeminiEmbeddingProvider(gemini_settings)
    client = RecordingGeminiClient(dimensions=3072)

    with pytest.raises(
        DependencyUnavailableError,
        match="Gemini embedding dimension mismatch: expected 768, got 3072",
    ):
        await provider._try_embed_batch(client, ["content"], "RETRIEVAL_DOCUMENT")
