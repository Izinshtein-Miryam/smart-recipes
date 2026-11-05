"""Image storage: validated uploads go to `pending/`, approval moves them to `public/`."""

import io
import uuid
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from app.config import get_settings

_SIGNATURES: dict[str, Callable[[bytes], bool]] = {
    "jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
}


class InvalidImageError(ValueError):
    pass


class ImageTooLargeError(InvalidImageError):
    """Maps to HTTP 413."""


class UnsupportedImageError(InvalidImageError):
    """Not a JPEG/PNG/WebP image; maps to HTTP 415."""


def detect_extension(data: bytes) -> str:
    for ext, matches in _SIGNATURES.items():
        if matches(data):
            return ext
    raise UnsupportedImageError("only JPEG, PNG and WebP images are allowed")


def _root() -> Path:
    return get_settings().storage_dir


def public_dir() -> Path:
    path = _root() / "public"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_pending(data: bytes) -> str:
    """Validates an upload, stores it as WebP under a random name and keeps the original.

    Returns the relative path of the WebP. The original lives in `originals/`.
    """
    if len(data) > get_settings().max_image_bytes:
        raise ImageTooLargeError("image is too large")
    ext = detect_extension(data)
    name = uuid.uuid4().hex
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            converted = img.convert("RGBA" if "A" in img.getbands() else "RGB")
            out = io.BytesIO()
            converted.save(out, format="WEBP", quality=85)
    except (OSError, Image.DecompressionBombError, ValueError) as exc:
        raise UnsupportedImageError("the file is not a valid image") from exc
    original = _root() / "originals" / f"{name}.{ext}"
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(data)
    rel = f"pending/{name}.webp"
    target = _root() / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(out.getvalue())
    return rel


def promote(rel: str) -> str:
    """Moves a pending image to the public folder; returns the new relative path."""
    if rel.startswith("public/"):
        return rel
    src = _root() / rel
    dest = public_dir() / src.name
    if src.exists():
        src.replace(dest)
    return f"public/{src.name}"


def delete(rel: str) -> None:
    path = _root() / rel
    path.unlink(missing_ok=True)
    for original in (_root() / "originals").glob(f"{path.stem}.*"):
        original.unlink(missing_ok=True)
