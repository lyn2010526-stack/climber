"""Tests for version CLI."""

import pytest
from click.testing import CliRunner

from app.cmds.version_cli import version_cli


class TestVersionCLI:
    """Tests for CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_list_command(self, runner):
        result = runner.invoke(version_cli, ['list'])
        assert result.exit_code == 0

    def test_get_command(self, runner):
        result = runner.invoke(version_cli, ['get', '1'])
        assert result.exit_code == 0

    def test_create_command(self, runner):
        result = runner.invoke(version_cli, ['create', '--name', 'Test'])
        assert result.exit_code == 0

