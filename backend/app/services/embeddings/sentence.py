"""sentence-transformers provider. Requires the `embeddings` extra."""

from typing import Any


class SentenceEmbeddingProvider:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model: Any = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        return [float(x) for x in self._model.encode(text)]
