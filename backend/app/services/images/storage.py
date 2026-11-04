"""Saving image files under MEDIA_DIR. Paths stored in the DB are relative to it."""

import secrets
from pathlib import Path

from app.config import get_settings


def save_image(recipe_id: int, data: bytes, kind: str) -> str:
    rel = Path("recipes") / str(recipe_id) / f"{secrets.token_hex(6)}-{kind}.webp"
    path = get_settings().media_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return rel.as_posix()


def delete_image(rel: str | None) -> None:
    if rel:
        (get_settings().media_dir / rel).unlink(missing_ok=True)
