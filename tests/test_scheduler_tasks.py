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


def test_global_executor_execution():
    """Verify the global ThreadPoolExecutor executes and returns correctly."""
    import time

    from app.core.tasks import get_task_result

    task_id = submit_task(dummy_task, 3, 5)

    # Poll for the result
    max_polls = 10
    result = None
    for _ in range(max_polls):
        res = get_task_result(task_id)
        if res and res["status"] == "completed":
            result = res["result"]
            break
        time.sleep(0.1)

    assert result == 8


def test_scheduler_initialized(app):
    """Verify that APScheduler is running and daily_backup is registered."""
    # Ensure scheduler is initialized for this test despite being in TESTING mode
    from app.core.scheduler import init_scheduler

    app.config["SCHEDULER_AUTOSTART"] = True
    try:
        init_scheduler(app)

        assert scheduler.running is True
        job = scheduler.get_job("daily_backup")
        assert job is not None
        assert job.trigger is not None
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
