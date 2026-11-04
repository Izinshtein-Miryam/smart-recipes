"""Google Gemini (Imagen) image provider. Requires the `images` extra."""

from app.services.images.provider import IMAGE_SYSTEM_PROMPT


class GeminiImageProvider:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def edit(self, image: bytes, instructions: str) -> bytes:
        raise NotImplementedError(f"TODO: Gemini image edit ({IMAGE_SYSTEM_PROMPT!r})")

    async def generate(self, prompt: str) -> bytes:
        raise NotImplementedError(f"TODO: Imagen generation ({IMAGE_SYSTEM_PROMPT!r})")
