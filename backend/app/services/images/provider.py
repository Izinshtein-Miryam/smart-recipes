"""Image provider abstraction (edit an uploaded photo / generate a new one)."""

import io
from typing import Protocol

from PIL import Image

from app.config import Settings

# Fixed system instruction attached to every image request.
IMAGE_SYSTEM_PROMPT = (
    "Show the dish only. No people, no hands, no human figures and no text in the image."
)


class ImageProvider(Protocol):
    async def edit(self, image: bytes, instructions: str) -> bytes: ...

    async def generate(self, prompt: str) -> bytes: ...


class MockImageProvider:
    """Returns a solid-color WebP image; used in development and tests."""

    def __init__(self) -> None:
        self.last_prompt: str | None = None

    async def edit(self, image: bytes, instructions: str) -> bytes:
        self.last_prompt = f"{IMAGE_SYSTEM_PROMPT}\n{instructions}"
        return to_webp(image)

    async def generate(self, prompt: str) -> bytes:
        self.last_prompt = f"{IMAGE_SYSTEM_PROMPT}\n{prompt}"
        img = Image.new("RGB", (800, 600), (246, 230, 218))
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        return buf.getvalue()


def to_webp(data: bytes, quality: int = 85) -> bytes:
    with Image.open(io.BytesIO(data)) as img:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="WEBP", quality=quality)
        return buf.getvalue()


def build_image_provider(settings: Settings) -> ImageProvider:
    if settings.image_provider == "gemini":
        from app.services.images.gemini import GeminiImageProvider

        return GeminiImageProvider(settings.gemini_api_key)
    return MockImageProvider()
