# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Cron-based task scheduler for automation workflows."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


@dataclass
class ScheduledTask:
    """A scheduled automation task."""

    name: str
    cron_expression: str
    callback: Callable[..., Any]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: datetime | None = None
    run_count: int = 0
    max_runs: int | None = None


class CronScheduler:
    """Simple cron-based scheduler for automation tasks.

    Supports standard 5-field cron expressions:
    minute hour day_of_month month day_of_week

    Examples:
    - "0 9 * * *"     -> Every day at 9:00 AM
    - "*/5 * * * *"   -> Every 5 minutes
    - "0 0 * * 1"     -> Every Monday at midnight
    """

    def __init__(self, max_concurrent: int = 3) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._max_concurrent = max_concurrent
        self._running = False

    def add_task(
        self,
        name: str,
        cron_expression: str,
        callback: Callable[..., Any],
        *args: Any,
        max_runs: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Schedule a new task."""
        if not self.validate_cron(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        self._tasks[name] = ScheduledTask(
            name=name,
            cron_expression=cron_expression,
            callback=callback,
            args=args,
            kwargs=kwargs,
            max_runs=max_runs,
        )

    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name in self._tasks:
            del self._tasks[name]
            return True
        return False

    def get_task(self, name: str) -> ScheduledTask | None:
        """Get a scheduled task by name."""
        return self._tasks.get(name)

    def list_tasks(self) -> list[ScheduledTask]:
        """List all scheduled tasks."""
        return list(self._tasks.values())

    @staticmethod
    def validate_cron(expression: str) -> bool:
        """Validate a cron expression (5 fields)."""
        parts = expression.strip().split()
        if len(parts) != 5:
            return False

        ranges = [
            (0, 59),   # minute
            (0, 23),   # hour
            (1, 31),   # day of month
            (1, 12),   # month
            (0, 7),    # day of week (0 and 7 = Sunday)
        ]

        for part, (min_val, max_val) in zip(parts, ranges):
            if not _validate_cron_field(part, min_val, max_val):
                return False

        return True

    @staticmethod
    def matches_now(
        cron_expression: str, now: datetime | None = None
    ) -> bool:
        """Check if a cron expression matches the current time."""
        now = now or datetime.now()
        parts = cron_expression.strip().split()
        if len(parts) != 5:
            return False

        checks = [
            (parts[0], now.minute),
            (parts[1], now.hour),
            (parts[2], now.day),
            (parts[3], now.month),
            (parts[4], now.isoweekday() % 7),  # Convert to 0=Sun
        ]

        return all(
            _field_matches(field_expr, value)
            for field_expr, value in checks
        )

    def get_due_tasks(
        self, now: datetime | None = None
    ) -> list[ScheduledTask]:
        """Get all tasks that are due to run."""
        due: list[ScheduledTask] = []
        for task in self._tasks.values():
            if not task.enabled:
                continue
            if task.max_runs is not None and task.run_count >= task.max_runs:
                continue
            if self.matches_now(task.cron_expression, now):
                due.append(task)
        return due

    def stop(self) -> None:
        """Signal the scheduler to stop."""
        self._running = False


def _validate_cron_field(field: str, min_val: int, max_val: int) -> bool:
    """Validate a single cron field."""
    if field == "*":
        return True

    # Handle */N (every N)
    if field.startswith("*/"):
        try:
            step = int(field[2:])
            return 1 <= step <= max_val
        except ValueError:
            return False

    # Handle comma-separated values
    for part in field.split(","):
        # Handle ranges (e.g., 1-5)
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                s, e = int(start), int(end)
                if not (min_val <= s <= max_val and min_val <= e <= max_val):
                    return False
            except ValueError:
                return False
        else:
            try:
                val = int(part)
                if not (min_val <= val <= max_val):
                    return False
            except ValueError:
                return False

    return True


def _field_matches(field_expr: str, value: int) -> bool:
    """Check if a time value matches a cron field expression."""
    if field_expr == "*":
        return True

    if field_expr.startswith("*/"):
        step = int(field_expr[2:])
        return value % step == 0

    for part in field_expr.split(","):
        if "-" in part:
            start, end = part.split("-", 1)
            if int(start) <= value <= int(end):
                return True
        elif int(part) == value:
            return True

    return False
