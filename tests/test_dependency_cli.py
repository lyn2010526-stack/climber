"""Tests for dependency CLI."""

import pytest
from click.testing import CliRunner

from app.cmds.dependency_cli import dependency_cli


class TestDependencyCLI:
    """Tests for CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_list_command(self, runner):
        result = runner.invoke(dependency_cli, ['list'])
        assert result.exit_code == 0

    def test_get_command(self, runner):
        result = runner.invoke(dependency_cli, ['get', '1'])
        assert result.exit_code == 0

    def test_create_command(self, runner):
        result = runner.invoke(dependency_cli, ['create', '--name', 'Test'])
        assert result.exit_code == 0

