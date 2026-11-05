"""Image storage: validated uploads go to `pending/`, approval moves them to `public/`."""

import uuid
from collections.abc import Callable
from pathlib import Path

from app.config import get_settings

_SIGNATURES: dict[str, Callable[[bytes], bool]] = {
    "jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
}


class InvalidImageError(ValueError):
    pass


def detect_extension(data: bytes) -> str:
    for ext, matches in _SIGNATURES.items():
        if matches(data):
            return ext
    raise InvalidImageError("only JPEG, PNG and WebP images are allowed")


def _root() -> Path:
    return get_settings().storage_dir


def public_dir() -> Path:
    path = _root() / "public"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_pending(data: bytes) -> str:
    """Validates and stores an upload under a random name; returns the relative path."""
    if len(data) > get_settings().max_image_bytes:
        raise InvalidImageError("image is too large")
    ext = detect_extension(data)
    rel = f"pending/{uuid.uuid4().hex}.{ext}"
    target = _root() / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
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
    (_root() / rel).unlink(missing_ok=True)
