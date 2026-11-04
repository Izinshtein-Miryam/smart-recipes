"""OpenAI embeddings provider (alternative to the local sentence-transformers model)."""

from typing import Any


class OpenAIEmbeddingProvider:
    """Synchronous client: embeddings are computed once, when a recipe is saved."""

    def __init__(self, api_key: str, model: str, timeout: float, client: Any | None = None) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self._client: Any = client

    def embed(self, text: str) -> list[float]:
        res = self._client.embeddings.create(model=self.model, input=text)
        return [float(x) for x in res.data[0].embedding]
