"""Tests for session CLI."""

import pytest
from click.testing import CliRunner

from app.cmds.session_cli import session_cli


class TestSessionCLI:
    """Tests for CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_list_command(self, runner):
        result = runner.invoke(session_cli, ['list'])
        assert result.exit_code == 0

    def test_get_command(self, runner):
        result = runner.invoke(session_cli, ['get', '1'])
        assert result.exit_code == 0

    def test_create_command(self, runner):
        result = runner.invoke(session_cli, ['create', '--name', 'Test'])
        assert result.exit_code == 0

