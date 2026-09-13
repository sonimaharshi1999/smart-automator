# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for the cron scheduler."""

from datetime import datetime

import pytest

from smart_automator.scheduler.cron_scheduler import CronScheduler


class TestCronScheduler:
    """Tests for CronScheduler."""

    def test_validate_cron_valid(self) -> None:
        assert CronScheduler.validate_cron("0 9 * * *") is True
        assert CronScheduler.validate_cron("*/5 * * * *") is True
        assert CronScheduler.validate_cron("0 0 * * 1") is True
        assert CronScheduler.validate_cron("30 14 1 * *") is True
        assert CronScheduler.validate_cron("0 0 1,15 * *") is True
        assert CronScheduler.validate_cron("0 9 * * 1-5") is True

    def test_validate_cron_invalid(self) -> None:
        assert CronScheduler.validate_cron("") is False
        assert CronScheduler.validate_cron("* * *") is False  # Too few fields
        assert CronScheduler.validate_cron("60 * * * *") is False  # Minute > 59
        assert CronScheduler.validate_cron("* 25 * * *") is False  # Hour > 23
        assert CronScheduler.validate_cron("abc * * * *") is False

    def test_matches_now(self) -> None:
        # Monday at 09:00
        dt = datetime(2026, 9, 14, 9, 0)  # Monday
        assert CronScheduler.matches_now("0 9 * * *", dt) is True
        assert CronScheduler.matches_now("0 10 * * *", dt) is False
        assert CronScheduler.matches_now("* 9 * * *", dt) is True
        assert CronScheduler.matches_now("0 9 * * 1", dt) is True  # Monday = 1

    def test_matches_every_5_minutes(self) -> None:
        dt_match = datetime(2026, 9, 14, 9, 15)
        dt_nomatch = datetime(2026, 9, 14, 9, 13)
        assert CronScheduler.matches_now("*/5 * * * *", dt_match) is True
        assert CronScheduler.matches_now("*/5 * * * *", dt_nomatch) is False

    def test_add_and_list_tasks(self) -> None:
        scheduler = CronScheduler()
        scheduler.add_task("task1", "0 9 * * *", lambda: None)
        scheduler.add_task("task2", "*/5 * * * *", lambda: None)
        tasks = scheduler.list_tasks()
        assert len(tasks) == 2

    def test_add_invalid_cron(self) -> None:
        scheduler = CronScheduler()
        with pytest.raises(ValueError, match="Invalid cron"):
            scheduler.add_task("bad", "invalid", lambda: None)

    def test_remove_task(self) -> None:
        scheduler = CronScheduler()
        scheduler.add_task("task1", "0 9 * * *", lambda: None)
        assert scheduler.remove_task("task1") is True
        assert scheduler.remove_task("task1") is False

    def test_get_due_tasks(self) -> None:
        scheduler = CronScheduler()
        scheduler.add_task("morning", "0 9 * * *", lambda: None)
        scheduler.add_task("evening", "0 18 * * *", lambda: None)

        dt = datetime(2026, 9, 14, 9, 0)
        due = scheduler.get_due_tasks(dt)
        assert len(due) == 1
        assert due[0].name == "morning"

    def test_max_runs_limit(self) -> None:
        scheduler = CronScheduler()
        scheduler.add_task("once", "* * * * *", lambda: None, max_runs=1)

        task = scheduler.get_task("once")
        assert task is not None
        task.run_count = 1

        due = scheduler.get_due_tasks()
        assert all(t.name != "once" for t in due)

    def test_disabled_task_not_due(self) -> None:
        scheduler = CronScheduler()
        scheduler.add_task("disabled", "* * * * *", lambda: None)
        task = scheduler.get_task("disabled")
        assert task is not None
        task.enabled = False

        due = scheduler.get_due_tasks()
        assert len(due) == 0
