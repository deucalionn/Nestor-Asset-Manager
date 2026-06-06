EMBEDDING_DIM = 384


def as_dict(result: object) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")  # type: ignore[union-attr]
    return result  # type: ignore[return-value]


class MockEmbeddingService:
    def __init__(self, vector: list[float] | None = None) -> None:
        self._vector = vector or ([1.0] + [0.0] * (EMBEDDING_DIM - 1))

    async def embed(self, text: str) -> list[float]:
        return list(self._vector)
