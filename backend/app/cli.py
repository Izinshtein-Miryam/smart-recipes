"""Management commands.

Usage:
    python -m app.cli create-sysadmin --email admin@example.com --name "מנהל"
    python -m app.cli seed
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.config import get_settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.models import Role, User
from app.seed import seed
from app.services.embeddings.provider import build_embedding_provider


def create_sysadmin(email: str, name: str, password: str | None) -> None:
    password = password or getpass.getpass("Password: ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email.lower())):
            sys.exit(f"User {email} already exists")
        db.add(
            User(
                email=email.lower(),
                password_hash=hash_password(password),
                display_name=name,
                role=Role.SYSADMIN,
            )
        )
        db.commit()
    print(f"System admin {email} created")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p_admin = sub.add_parser("create-sysadmin", help="Create the first system admin")
    p_admin.add_argument("--email", required=True)
    p_admin.add_argument("--name", default="מנהל מערכת")
    p_admin.add_argument("--password", help="Prompted if omitted")

    sub.add_parser("seed", help="Load demo recipes")

    args = parser.parse_args(argv)
    if args.command == "create-sysadmin":
        create_sysadmin(args.email, args.name, args.password)
    elif args.command == "seed":
        with SessionLocal() as db:
            embedder = build_embedding_provider(get_settings())
            print(f"Seeded {seed(db, embedder)} recipes")


if __name__ == "__main__":
    main()
