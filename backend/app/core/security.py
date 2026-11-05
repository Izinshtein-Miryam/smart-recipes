"""Admin password check (bcrypt) and JWT helpers."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # malformed hash in configuration
        return False


def create_admin_token() -> str:
    s = get_settings()
    expire = datetime.now(UTC) + timedelta(hours=s.jwt_expire_hours)
    return jwt.encode({"sub": "admin", "exp": expire}, s.jwt_secret, algorithm=s.jwt_algorithm)


def is_valid_admin_token(token: str) -> bool:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError:
        return False
    return payload.get("sub") == "admin"
