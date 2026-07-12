"""Tests for scheduler and async task components."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from app.core.scheduler import scheduler
from app.core.tasks import submit_task


def dummy_task(x, y):
    """Simple task for testing the executor."""
    return x + y


# ThreadPoolExecutor was replaced by Celery. Async execution is tested in test_tasks_celery.py.


def test_scheduler_initialized(app):
    """Verify that APScheduler is running and cover_cleanup_watchdog is registered."""
    # Ensure scheduler is initialized for this test despite being in TESTING mode
    from app.core.scheduler import init_scheduler

    app.config["SCHEDULER_AUTOSTART"] = True
    try:
        init_scheduler(app)

        assert scheduler.running is True
        job = scheduler.get_job("cover_cleanup_watchdog")
        assert job is not None
        assert job.trigger is not None
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
