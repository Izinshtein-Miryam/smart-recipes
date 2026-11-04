"""Maintenance commands: `python -m app.cli <command>`."""

import argparse
import getpass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Recipe, RecipeStatus
from app.services import storage


def hash_admin_password() -> None:
    """Prints a bcrypt hash to put in ADMIN_PASSWORD_HASH (wrap it in single quotes in .env files)."""
    print(hash_password(getpass.getpass("Admin password: ")))


def purge_rejected() -> None:
    """Deletes images of recipes rejected more than N days ago (default 7)."""
    cutoff = datetime.now(UTC) - timedelta(days=get_settings().rejected_image_retention_days)
    with SessionLocal() as db:
        stmt = select(Recipe).where(
            Recipe.status == RecipeStatus.REJECTED,
            Recipe.image_path.is_not(None),
            Recipe.created_at < cutoff,
        )
        recipes = list(db.scalars(stmt))
        for recipe in recipes:
            if recipe.image_path:
                storage.delete(recipe.image_path)
            recipe.image_path = None
        db.commit()
    print(f"purged {len(recipes)} image(s)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    parser.add_argument("command", choices=["hash-admin-password", "purge-rejected"])
    args = parser.parse_args()
    {"hash-admin-password": hash_admin_password, "purge-rejected": purge_rejected}[args.command]()


if __name__ == "__main__":
    main()
