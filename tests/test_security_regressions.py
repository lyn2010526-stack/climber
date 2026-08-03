"""Focused regressions for credential and path-safety fixes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.api_key_crypto import decrypt_api_key, encrypt_api_key
from app.core.memory_tools import MemoryToolRegistry
from app.core.sandbox import SandboxConfig, SandboxExecutor


def test_api_key_encryption_round_trip() -> None:
    original = "sk-test-secret"

    encrypted = encrypt_api_key(original)

    assert encrypted.startswith("enc:v1:")
    assert original not in encrypted
    assert decrypt_api_key(encrypted) == original


def test_api_key_decryption_accepts_legacy_plaintext() -> None:
    assert decrypt_api_key("legacy-plaintext-key") == "legacy-plaintext-key"


@pytest.mark.asyncio
async def test_core_memory_replace_reports_success() -> None:
    class MemoryService:
        async def get_block(self, **_kwargs):
            return SimpleNamespace(value="old value")

        async def replace_in_block(self, **_kwargs):
            return SimpleNamespace(value="new value")

    registry = MemoryToolRegistry(memory_service=MemoryService())

    result = await registry._tool_core_memory_replace("profile", "old", "new")

    assert result == "Replaced text in block 'profile'"


@pytest.mark.asyncio
async def test_core_memory_replace_reports_missing_text() -> None:
    class MemoryService:
        async def get_block(self, **_kwargs):
            return SimpleNamespace(value="current value")

        async def replace_in_block(self, **_kwargs):
            raise AssertionError("replace should not run when old text is missing")

    registry = MemoryToolRegistry(memory_service=MemoryService())

    result = await registry._tool_core_memory_replace("profile", "old", "new")

    assert result.startswith("Warning: old text not found")


@pytest.mark.asyncio
async def test_sandbox_blocks_parent_directory_traversal(tmp_path) -> None:
    sandbox = SandboxExecutor(SandboxConfig(workdir=str(tmp_path)))

    result = await sandbox.execute("cat ../secret.txt")

    assert result.startswith("BLOCKED:")


@pytest.mark.asyncio
async def test_sandbox_blocks_absolute_path_outside_workdir(tmp_path) -> None:
    sandbox = SandboxExecutor(SandboxConfig(workdir=str(tmp_path)))

    result = await sandbox.execute("cat /tmp/outside.txt")

    assert result.startswith("BLOCKED:")
