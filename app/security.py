import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from app.config import settings


PBKDF2_ITERATIONS = 210_000


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(PBKDF2_ITERATIONS),
            _b64url_encode(salt),
            _b64url_encode(digest),
        ]
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64url_decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(_b64url_encode(digest), expected_digest)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_expires_minutes)).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}

    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(f"{header_part}.{payload_part}")
    return f"{header_part}.{payload_part}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недійсний або прострочений токен авторизації.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        header_part, payload_part, signature = token.split(".", 2)
    except ValueError as exc:
        raise credentials_error from exc

    expected_signature = _sign(f"{header_part}.{payload_part}")
    if not hmac.compare_digest(signature, expected_signature):
        raise credentials_error

    try:
        header = json.loads(_b64url_decode(header_part))
        payload = json.loads(_b64url_decode(payload_part))
    except (json.JSONDecodeError, ValueError) as exc:
        raise credentials_error from exc

    if header.get("alg") != "HS256":
        raise credentials_error

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(datetime.now(timezone.utc).timestamp()):
        raise credentials_error

    if not payload.get("sub"):
        raise credentials_error

    return payload


def _sign(value: str) -> str:
    digest = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        value.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)
