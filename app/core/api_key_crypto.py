"""Reversible encryption for provider API keys."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.app_secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_api_key(api_key: str) -> str:
    if not api_key or api_key.startswith(_PREFIX):
        return api_key
    token = _fernet().encrypt(api_key.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt_api_key(value: str) -> str:
    if not value or not value.startswith(_PREFIX):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX) :].encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("API key cannot be decrypted with the configured app secret") from exc
