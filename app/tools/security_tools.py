"""Security and encryption tools."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import string

import structlog
from cryptography.fernet import Fernet

from app.tools import ToolRegistry

logger = structlog.get_logger()


class SecurityTools:
                """Security, encryption, and hashing tools."""

                def register(self, registry: ToolRegistry) -> None:
                    """Register all security tools."""
                    registry.register(
                        name="sec_hash",
                        description="Generate cryptographic hash of data",
                        parameters={
                            "type": "object",
                            "properties": {
                                "data": {"type": "string", "description": "Data to hash"},
                                "algorithm": {"type": "string", "description": "Hash algorithm (sha256, sha512, md5, blake2b)"},
                                "encoding": {"type": "string", "description": "Input encoding"},
                            },
                            "required": ["data"],
                        },
                        func=self.hash_data,
                    )
                    registry.register(
                        name="sec_hmac",
                        description="Generate HMAC signature.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "data": {"type": "string"},
                                "key": {"type": "string"},
                                "algorithm": {"type": "string"},
                            },
                            "required": ["data", "key"],
                        },
                        func=self.generate_hmac,
                    )
                    registry.register(
                        name="sec_encrypt",
                        description="Encrypt data with symmetric encryption",
                        parameters={
                            "type": "object",
                            "properties": {
                                "data": {"type": "string"},
                                "key": {"type": "string", "description": "Encryption key (32 bytes base64)"},
                            },
                            "required": ["data", "key"],
                        },
                        func=self.encrypt_data,
                    )
                    registry.register(
                        name="sec_decrypt",
                        description="Decrypt symmetrically encrypted data",
                        parameters={
                            "type": "object",
                            "properties": {
                                "encrypted_data": {"type": "string"},
                                "key": {"type": "string"},
                            },
                            "required": ["encrypted_data", "key"],
                        },
                        func=self.decrypt_data,
                    )
                    registry.register(
                        name="sec_generate_key",
                        description="Generate encryption key",
                        parameters={
                            "type": "object",
                            "properties": {
                                "algorithm": {"type": "string"},
                            },
                            "required": [],
                        },
                        func=self.generate_key,
                    )
                    registry.register(
                        name="sec_password_strength",
                        description="Check password strength",
                        parameters={
                            "type": "object",
                            "properties": {
                                "password": {"type": "string"},
                            },
                            "required": ["password"],
                        },
                        func=self.check_password_strength,
                    )
                    registry.register(
                        name="sec_generate_password",
                        description="Generate secure random password",
                        parameters={
                            "type": "object",
                            "properties": {
                                "length": {"type": "integer"},
                                "include_uppercase": {"type": "boolean"},
                                "include_numbers": {"type": "boolean"},
                                "include_symbols": {"type": "boolean"},
                            },
                            "required": [],
                        },
                        func=self.generate_password,
                    )
                    registry.register(
                        name="sec_generate_token",
                        description="Generate secure random token",
                        parameters={
                            "type": "object",
                            "properties": {
                                "length": {"type": "integer"},
                                "format": {"type": "string"},
                            },
                            "required": [],
                        },
                        func=self.generate_token,
                    )
                    registry.register(
                        name="sec_compare",
                        description="Timing-safe string comparison",
                        parameters={
                            "type": "object",
                            "properties": {
                                "a": {"type": "string"},
                                "b": {"type": "string"},
                            },
                            "required": ["a", "b"],
                        },
                        func=self.timing_safe_compare,
                    )

                def hash_data(self, data: str, algorithm: str = "sha256", encoding: str = "utf-8") -> dict:
                    """Generate cryptographic hash."""
                    algo_map = {
                        "md5": hashlib.md5,
                        "sha1": hashlib.sha1,
                        "sha256": hashlib.sha256,
                        "sha384": hashlib.sha384,
                        "sha512": hashlib.sha512,
                        "blake2b": hashlib.blake2b,
                    }
                    hasher = algo_map.get(algorithm, hashlib.sha256)()
                    hasher.update(data.encode(encoding))
                    return {
                        "algorithm": algorithm,
                        "hash": hasher.hexdigest(),
                        "length": hasher.digest_size * 8,
                    }

                def generate_hmac(self, data: str, key: str, algorithm: str = "sha256") -> dict:
                    """Generate HMAC signature."""
                    algo_map = {
                        "sha256": hashlib.sha256,
                        "sha512": hashlib.sha512,
                        "sha1": hashlib.sha1,
                    }
                    hash_func = algo_map.get(algorithm, hashlib.sha256)
                    signature = hmac.new(key.encode(), data.encode(), hash_func).hexdigest()
                    return {
                        "algorithm": algorithm,
                        "signature": signature,
                        "data_length": len(data),
                    }

                def encrypt_data(self, data: str, key: str) -> dict:
                    """Encrypt data using Fernet symmetric encryption."""
                    try:
                        f = Fernet(key.encode())
                        encrypted = f.encrypt(data.encode())
                        return {
                            "encrypted": encrypted.decode(),
                            "algorithm": "Fernet",
                        }
                    except Exception as e:
                        return {"error": str(e)}

                def decrypt_data(self, encrypted_data: str, key: str) -> dict:
                    """Decrypt Fernet-encrypted data."""
                    try:
                        f = Fernet(key.encode())
                        decrypted = f.decrypt(encrypted_data.encode())
                        return {
                            "decrypted": decrypted.decode(),
                        }
                    except Exception as e:
                        return {"error": str(e)}

                def generate_key(self, algorithm: str = "fernet") -> dict:
                    """Generate encryption key."""
                    if algorithm == "fernet":
                        key = Fernet.generate_key()
                        return {"key": key.decode(), "algorithm": algorithm}
                    elif algorithm == "random":
                        key = secrets.token_hex(32)
                        return {"key": key, "algorithm": algorithm}
                    return {"error": f"Unknown algorithm: {algorithm}"}

                def check_password_strength(self, password: str) -> dict:
                    """Evaluate password strength."""
                    score = 0
                    feedback = []

                    if len(password) >= 8:
                        score += 1
                    else:
                        feedback.append("Password should be at least 8 characters")

                    if len(password) >= 12:
                        score += 1
                    if len(password) >= 16:
                        score += 1

                    if re.search(r"[a-z]", password):
                        score += 1
                    else:
                        feedback.append("Add lowercase letters")

                    if re.search(r"[A-Z]", password):
                        score += 1
                    else:
                        feedback.append("Add uppercase letters")

                    if re.search(r"[0-9]", password):
                        score += 1
                    else:
                        feedback.append("Add numbers")

                    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                        score += 1
                    else:
                        feedback.append("Add special characters")

                    # Check for common patterns
                    common = ["password", "123456", "qwerty", "admin", "letmein"]
                    if password.lower() in common:
                        score = 0
                        feedback.append("Password is too common")

                    strength_levels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
                    level = min(score // 2, len(strength_levels) - 1)

                    return {
                        "score": score,
                        "max_score": 8,
                        "strength": strength_levels[level],
                        "feedback": feedback,
                    }

                def generate_password(
                    self, length: int = 16, include_uppercase: bool = True,
                    include_numbers: bool = True, include_symbols: bool = True,
                ) -> dict:
                    """Generate secure random password."""
                    chars = string.ascii_lowercase
                    if include_uppercase:
                        chars += string.ascii_uppercase
                    if include_numbers:
                        chars += string.digits
                    if include_symbols:
                        chars += "!@#$%^&*"

                    if not chars:
                        chars = string.ascii_lowercase

                    password = "".join(secrets.choice(chars) for _ in range(length))
                    return {
                        "password": password,
                        "length": length,
                        "entropy_bits": length * (len(chars).bit_length()),
                    }

                def generate_token(self, length: int = 32, format: str = "hex") -> dict:
                    """Generate secure random token."""
                    if format == "hex":
                        token = secrets.token_hex(length)
                    elif format == "urlsafe":
                        token = secrets.token_urlsafe(length)
                    elif format == "alphanumeric":
                        token = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))
                    else:
                        token = secrets.token_hex(length)

                    return {
                        "token": token,
                        "length": len(token),
                        "format": format,
                    }

                def timing_safe_compare(self, a: str, b: str) -> dict:
                    """Timing-safe string comparison to prevent timing attacks."""
                    result = hmac.compare_digest(a.encode(), b.encode())
                    return {
                        "equal": result,
                        "method": "hmac.compare_digest",
                    }
