"""Scheduled background jobs manager."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging

from flask_apscheduler import APScheduler
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)
scheduler = APScheduler()


def run_scheduled_cover_cleanup():
    """Periodic watchdog that resets cover tasks stuck in pending/processing."""
    try:
        from app.utils.covers import cleanup_stuck_pending_covers

        with scheduler.app.app_context():
            stuck = cleanup_stuck_pending_covers(timeout_minutes=15)
            if stuck > 0:
                logger.info("Cover cleanup: cleared %d stuck tasks", stuck)
    except (SQLAlchemyError, ValueError, AttributeError, KeyError, RuntimeError):
        logger.exception("Cover cleanup job failed")


def init_scheduler(app):
    """Initializes the APScheduler and registers jobs."""
    if app.config.get("TESTING") and not app.config.get("SCHEDULER_AUTOSTART", False):
        logger.debug("APScheduler execution skipped in testing mode.")
        return

    if scheduler.running:
        logger.debug("APScheduler already running, skipping initialization.")
        return

    # Scheduler configuration
    app.config["SCHEDULER_API_ENABLED"] = False

    try:
        scheduler.init_app(app)

        # Runtime watchdog: clear stuck cover tasks every 5 minutes
        scheduler.add_job(
            id="cover_cleanup_watchdog",
            func=run_scheduled_cover_cleanup,
            trigger="interval",
            minutes=5,
            replace_existing=True,
        )

        scheduler.start()
        logger.info("APScheduler initialized and started.")
    except (SQLAlchemyError, ValueError, AttributeError, RuntimeError) as e:
        # Handle cases where scheduler might have started between the check and start()
        if "already running" in str(e).lower():
            logger.debug("APScheduler reported already running during start.")
        else:
            logger.error(f"Failed to initialize APScheduler: {e}")
