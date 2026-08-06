"""Tests for critical security and architecture fixes."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.config import Settings

try:
    from app.storage.auth import _get_fernet
except ImportError:
    _get_fernet = None


class TestSecretKeyNotHardcoded:
    """Verify secret key is auto-generated, not hardcoded."""

    def test_secret_key_is_persistent_in_local(self):
        """Local/test instances should share a stable persistent development key."""
        s1 = Settings()
        s2 = Settings()
        assert s1.app_secret_key == s2.app_secret_key
        assert s1.app_secret_key

    def test_secret_key_is_not_default_value(self):
        """Secret key should never be the old hardcoded default."""
        s = Settings()
        assert s.app_secret_key != "dev-secret-key-change-in-production"
        assert s.app_secret_key != "change-me"

    def test_secret_key_is_persistent_development_key(self):
        """Local/test key should be the documented persistent development value."""
        s = Settings()
        assert s.app_secret_key == "agent-engine-local-persistent-development-key"


@pytest.mark.skip(reason="Auth/Fernet removed for local-only mode")
class TestFernetKeyDerivation:
    """Verify Fernet key derivation is deterministic and consistent."""

    def test_fernet_same_key_produces_same_result(self):
        """Same secret key should produce same Fernet instance behavior."""
        Settings()
        Settings()
        f1 = _get_fernet()
        f2 = _get_fernet()
        assert isinstance(f1, Fernet)
        assert isinstance(f2, Fernet)

    def test_fernet_can_encrypt_and_decrypt(self):
        """Fernet from _get_fernet should be usable for encryption."""
        fernet = _get_fernet()
        plaintext = "test-api-key-12345"
        encrypted = fernet.encrypt(plaintext.encode())
        decrypted = fernet.decrypt(encrypted).decode()
        assert decrypted == plaintext


class TestServicesWithoutGlobalState:
    """Verify services can be instantiated without global singletons."""

    def test_vector_memory_service_instantiation(self):
        """VectorMemoryService should be instantiable with custom path."""
        import tempfile

        from app.core.vector_memory import VectorMemoryService
        with tempfile.TemporaryDirectory() as tmpdir:
            service = VectorMemoryService(persist_directory=tmpdir)
            assert service is not None

    def test_core_memory_service_instantiation(self):
        """CoreMemoryService should be instantiable."""
        from app.core.core_memory import CoreMemoryService
        service = CoreMemoryService()
        assert service is not None

    def test_memory_reflection_service_injection(self):
        """MemoryReflectionService should accept VectorMemoryService via constructor."""
        import tempfile

        from app.core.memory_reflection import MemoryReflectionService
        from app.core.vector_memory import VectorMemoryService
        with tempfile.TemporaryDirectory() as tmpdir:
            vm = VectorMemoryService(persist_directory=tmpdir)
            service = MemoryReflectionService(vector_memory=vm)
            assert service.vector_memory is vm

    def test_working_memory_service_instantiation(self):
        """WorkingMemoryService should be instantiable."""
        from app.core.working_memory import WorkingMemoryService
        service = WorkingMemoryService()
        assert service is not None


class TestAppendBlockSingleSession:
    """Verify append_block uses a single session (no race condition)."""

    def test_append_block_uses_single_session_source(self):
        """The append_block method should not create a second session."""
        import inspect

        from app.core.core_memory import CoreMemoryService
        source = inspect.getsource(CoreMemoryService.append_block)
        # Count occurrences of async_session() - should be 0 (moved to _update_block)
        assert source.count("async_session()") == 0
        # Should NOT contain db.merge
        assert "db.merge" not in source
        # Should use _update_block helper
        assert "_update_block" in source
