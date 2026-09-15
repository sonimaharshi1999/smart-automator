# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for CLI commands."""

from click.testing import CliRunner

from smart_automator.cli import cli


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_info_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "SmartAutomator" in result.output
        assert "Prompt" in result.output
        assert "Screenshot" in result.output
        assert "Recording" in result.output

    def test_platforms_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["platforms"])
        # Should not crash even with no platform configs
        assert result.exit_code == 0

    def test_schedule_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["schedule"])
        assert result.exit_code == 0

    def test_run_dry_run(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, [
            "run", "Test instruction", "--dry-run", "-p", "generic"
        ])
        # May fail if no LLM available, but should not crash
        assert result.exit_code == 0 or "Claude CLI not found" in result.output
