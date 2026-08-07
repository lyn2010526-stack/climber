"""Tests for team CLI."""

import pytest
from click.testing import CliRunner

from app.cmds.team_cli import team_cli


class TestTeamCLI:
    """Tests for CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_list_command(self, runner):
        result = runner.invoke(team_cli, ['list'])
        assert result.exit_code == 0

    def test_get_command(self, runner):
        result = runner.invoke(team_cli, ['get', '1'])
        assert result.exit_code == 0

    def test_create_command(self, runner):
        result = runner.invoke(team_cli, ['create', '--name', 'Test'])
        assert result.exit_code == 0

