import math
from typing import Protocol

from nam_agentic.settings import settings


def canonical_embed_text(title: str, content: str) -> str:
    return f"{title}\n\n{content}"


def news_embed_text(
    title: str,
    summary: str | None = None,
    content_markdown: str | None = None,
) -> str:
    parts = [title]
    if summary:
        parts.append(summary)
    if content_markdown:
        parts.append(content_markdown)
    return "\n\n".join(parts)


class EmbeddingService(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class OllamaEmbeddingService:
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        expected_dim: int | None = None,
    ) -> None:
        self._model = model or settings.embedding_model
        self._base_url = base_url or settings.llm_base_url
        self._expected_dim = expected_dim or settings.embedding_dim

    async def embed(self, text: str) -> list[float]:
        from langchain_ollama import OllamaEmbeddings

        client = OllamaEmbeddings(model=self._model, base_url=self._base_url)
        vector = await client.aembed_query(text)
        return fit_embedding_dimension(vector, self._expected_dim)


def fit_embedding_dimension(vector: list[float], target_dim: int) -> list[float]:
    """Match pgvector column size; Matryoshka-truncate when the model returns more dims."""
    if len(vector) == target_dim:
        return vector
    if len(vector) > target_dim:
        return _truncate_and_normalize(vector, target_dim)
    msg = f"Expected embedding dimension at least {target_dim}, got {len(vector)}"
    raise ValueError(msg)


def _truncate_and_normalize(vector: list[float], target_dim: int) -> list[float]:
    sliced = [float(value) for value in vector[:target_dim]]
    norm = math.sqrt(sum(value * value for value in sliced))
    if norm == 0:
        return sliced
    return [value / norm for value in sliced]
