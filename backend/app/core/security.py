import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import argon2
import jwt

from app.core.config import settings

_password_hasher = argon2.PasswordHasher()

DUMMY_HASH = _password_hasher.hash("timing-equalization-dummy")


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except argon2.exceptions.VerifyMismatchError:
        return False


def create_access_token(account_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(account_id),
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
        "iat": now,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(account_id: uuid.UUID) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": str(account_id),
        "exp": expires_at,
        "iat": now,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    raw_token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash, expires_at


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def decode_refresh_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
