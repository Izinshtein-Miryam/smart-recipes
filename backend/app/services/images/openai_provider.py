"""OpenAI image provider (GPT Image): edit an uploaded photo or generate a new one."""

import base64
from typing import Any

from app.services.images.provider import IMAGE_SYSTEM_PROMPT, to_webp


def _decode(res: Any) -> bytes:
    if not res.data or not res.data[0].b64_json:
        raise RuntimeError("OpenAI image response contained no image data")
    return to_webp(base64.b64decode(res.data[0].b64_json))


class OpenAIImageProvider:
    """`client` may be injected (tests). Results are returned as WebP bytes."""

    def __init__(self, api_key: str, model: str, timeout: float, client: Any | None = None) -> None:
        if client is None:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self._client: Any = client

    async def edit(self, image: bytes, instructions: str) -> bytes:
        res = await self._client.images.edit(
            model=self.model,
            image=("image.png", image, "image/png"),
            prompt=f"{IMAGE_SYSTEM_PROMPT}\n{instructions}",
        )
        return _decode(res)

    async def generate(self, prompt: str) -> bytes:
        res = await self._client.images.generate(
            model=self.model,
            prompt=f"{IMAGE_SYSTEM_PROMPT}\n{prompt}",
            size="1536x1024",
        )
        return _decode(res)
