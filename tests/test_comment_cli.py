"""Tests for comment CLI."""

import pytest
from click.testing import CliRunner

from app.cmds.comment_cli import comment_cli


class TestCommentCLI:
    """Tests for CLI."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_list_command(self, runner):
        result = runner.invoke(comment_cli, ['list'])
        assert result.exit_code == 0

    def test_get_command(self, runner):
        result = runner.invoke(comment_cli, ['get', '1'])
        assert result.exit_code == 0

    def test_create_command(self, runner):
        result = runner.invoke(comment_cli, ['create', '--name', 'Test'])
        assert result.exit_code == 0

