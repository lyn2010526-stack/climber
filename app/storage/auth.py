"""Authentication & security utilities — encryption only, local-only mode."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from cryptography.fernet import Fernet

from app.config import settings

_fernet_instance: Fernet | None = None


def _get_fernet_key() -> bytes:
    key = settings.app_secret_key or "dev-secret-key-change-in-production"
    key_bytes = key.encode()
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b"\x00")[:32]
    else:
        key_bytes = key_bytes[:32]
    return base64.urlsafe_b64encode(key_bytes)


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = Fernet(_get_fernet_key())
    return _fernet_instance


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${pw_hash.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hash_hex = stored.split("$", 1)
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return hmac.compare_digest(pw_hash.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def encrypt_api_key(plain_key: str) -> str:
    fernet = _get_fernet()
    return fernet.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_hex: str) -> str:
    fernet = _get_fernet()
    return fernet.decrypt(encrypted_hex.encode()).decode()