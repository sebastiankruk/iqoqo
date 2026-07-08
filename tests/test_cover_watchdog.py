# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Regression tests for the cover watchdog scheduler and Celery task time limits.

Bugs found on pre.iqoqo.cc (2026-07-08) and fixed in commits 0c33d1a + 9bb409c:

1. Celery tasks had no hard time limit, so a worker could be consumed forever by
   a stuck cover pipeline.  Fixed: task_time_limit=600 + task_soft_time_limit=540.

2. The only stuck-cover cleanup ran once at Flask startup.  If a task crashed
   post-startup (Gemini 403 scenario), cover_status stayed 'processing' forever.
   Fixed: recurring APScheduler job 'cover_cleanup_watchdog' every 5 minutes.
"""

import logging
from unittest.mock import patch

# ─── Celery time-limit regression tests ──────────────────────────────────────


def test_celery_task_time_limit_configured():
    """Regression: Celery must have a hard task_time_limit to kill stuck cover tasks."""
    from app.core.celery_app import celery

    assert celery.conf.task_time_limit is not None, "task_time_limit must be set"
    assert celery.conf.task_time_limit >= 60, f"task_time_limit should be at least 60 s, got {celery.conf.task_time_limit}"


def test_celery_soft_time_limit_configured():
    """Regression: Celery must have a soft time limit for graceful cleanup before hard kill."""
    from app.core.celery_app import celery

    assert celery.conf.task_soft_time_limit is not None, "task_soft_time_limit must be set"
    assert celery.conf.task_soft_time_limit >= 60, f"task_soft_time_limit should be at least 60 s, got {celery.conf.task_soft_time_limit}"
    assert (
        celery.conf.task_soft_time_limit < celery.conf.task_time_limit
    ), "task_soft_time_limit must be less than task_time_limit to allow graceful cleanup"


# ─── APScheduler watchdog regression tests ────────────────────────────────────


def test_cover_cleanup_watchdog_job_registered(app):
    """Regression: APScheduler must register a recurring cover cleanup job."""
    from app.core.scheduler import init_scheduler, scheduler

    app.config["SCHEDULER_AUTOSTART"] = True
    try:
        init_scheduler(app)

        assert scheduler.running is True, "Scheduler must be running"
        job = scheduler.get_job("cover_cleanup_watchdog")
        assert job is not None, "'cover_cleanup_watchdog' job must be registered in APScheduler"
        assert job.trigger is not None
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_run_scheduled_cover_cleanup_calls_cleanup(app):
    """Regression: run_scheduled_cover_cleanup must invoke cleanup_stuck_pending_covers."""
    from app.core.scheduler import run_scheduled_cover_cleanup

    with app.app_context():
        # cleanup_stuck_pending_covers is lazy-imported inside run_scheduled_cover_cleanup,
        # so we patch at its definition site in app.utils.covers.
        with patch("app.utils.covers.cleanup_stuck_pending_covers", return_value=0) as mock_cleanup:
            run_scheduled_cover_cleanup()
            mock_cleanup.assert_called_once()


def test_run_scheduled_cover_cleanup_logs_cleared_count(app, caplog):
    """Regression: run_scheduled_cover_cleanup must log when stuck tasks are cleared."""
    from app.core.scheduler import run_scheduled_cover_cleanup

    with app.app_context():
        with patch("app.utils.covers.cleanup_stuck_pending_covers", return_value=3):
            with caplog.at_level(logging.INFO, logger="app.core.scheduler"):
                run_scheduled_cover_cleanup()

    assert any("3" in record.message for record in caplog.records), "Expected log entry mentioning the count of cleared stuck tasks"


def test_run_scheduled_cover_cleanup_survives_exception(app):
    """Regression: run_scheduled_cover_cleanup must not propagate exceptions.

    The scheduler job must be resilient so an error in the cleanup does not
    crash the APScheduler job loop.
    """
    from app.core.scheduler import run_scheduled_cover_cleanup

    with app.app_context():
        with patch("app.utils.covers.cleanup_stuck_pending_covers", side_effect=RuntimeError("DB down")):
            # Must not raise
            run_scheduled_cover_cleanup()


def test_cover_cleanup_watchdog_interval_is_reasonable(app):
    """Regression: the watchdog interval must be <= 15 minutes to limit stuck-task exposure."""
    from app.core.scheduler import init_scheduler, scheduler

    app.config["SCHEDULER_AUTOSTART"] = True
    try:
        init_scheduler(app)

        job = scheduler.get_job("cover_cleanup_watchdog")
        assert job is not None

        # IntervalTrigger exposes `interval` as datetime.timedelta
        interval_seconds = job.trigger.interval.total_seconds()
        assert (
            interval_seconds <= 900
        ), f"cover_cleanup_watchdog fires every {interval_seconds}s — too infrequent (max 900s)"  # 15 minutes max
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
