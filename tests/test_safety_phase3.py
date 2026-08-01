"""TDD: Phase 3 — L3 Docker container isolation."""

import os
import pytest

os.environ.setdefault("APP_TESTING", "true")

from app.core.docker_sandbox import DockerSandbox, DockerSandboxConfig


def test_docker_availability_check():
    ds = DockerSandbox()
    available = ds.available
    assert isinstance(available, bool)


def test_docker_fallback_when_unavailable():
    ds = DockerSandbox()
    if ds.available:
        pytest.skip("Docker is available, skipping fallback test")

    import asyncio
    result = asyncio.run(ds.execute(["echo", "hello"], "/tmp"))
    assert result.returncode == -1


@pytest.mark.skipif(
    not DockerSandbox().available,
    reason="Docker not available",
)
class TestDockerSandboxLive:
    """Tests that require a running Docker daemon."""

    def setup_method(self):
        self.ds = DockerSandbox(DockerSandboxConfig(
            image="python:3.11-slim",
            timeout_seconds=30,
        ))

    def test_execute_safe_command(self):
        import asyncio
        result = asyncio.run(self.ds.execute(["echo", "hello"], "/tmp"))
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_execute_python_code(self):
        import asyncio
        result = asyncio.run(self.ds.execute(
            ["python3", "-c", "print(1+1)"],
            "/tmp",
        ))
        assert result.returncode == 0
        assert "2" in result.stdout

    def test_network_isolation(self):
        import asyncio
        result = asyncio.run(self.ds.execute(
            ["python3", "-c", "import urllib.request; urllib.request.urlopen(\"http://example.com\")"],
            "/tmp",
        ))
        assert result.returncode != 0

    def test_readonly_filesystem(self):
        import asyncio
        result = asyncio.run(self.ds.execute(
            ["sh", "-c", "echo test > /etc/testfile"],
            "/tmp",
        ))
        assert result.returncode != 0

    def test_timeout_enforcement(self):
        import asyncio
        result = asyncio.run(self.ds.execute(
            ["sleep", "60"],
            "/tmp",
        ))
        assert result.timed_out or result.returncode != 0

    def test_workspace_writable(self):
        import asyncio
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = asyncio.run(self.ds.execute(
                ["sh", "-c", "echo hello > /workspace/test.txt"],
                tmp,
            ))
            assert result.returncode == 0
            assert os.path.exists(os.path.join(tmp, "test.txt"))

    def test_container_cleanup(self):
        import asyncio
        import docker
        client = docker.from_env()
        before = len(client.containers.list(all=True, filters={"name": "sandbox_"}))
        asyncio.run(self.ds.execute(["echo", "test"], "/tmp"))
        after = len(client.containers.list(all=True, filters={"name": "sandbox_"}))
        assert after <= before
