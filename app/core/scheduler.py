"""Scheduled background jobs manager."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging

from flask_apscheduler import APScheduler

logger = logging.getLogger(__name__)
scheduler = APScheduler()


def run_scheduled_backup():
    """Wrapper to run the backup job within the application context."""
    logger.info("Executing scheduled backup job...")
    try:
        from flask import current_app

        from scripts.backup import create_export

        create_export(current_app)
        logger.info("Scheduled backup job completed successfully.")
    except Exception:  # pylint: disable=broad-exception-caught # noqa: BLE001
        logger.exception("Scheduled backup job failed.")


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

        # Add the daily backup job based on environment variables
        scheduler.add_job(
            id="daily_backup",
            func=run_scheduled_backup,
            trigger="cron",
            hour=app.config.get("BACKUP_CRON_HOUR", "3"),
            minute=app.config.get("BACKUP_CRON_MINUTE", "0"),
            replace_existing=True,
        )

        scheduler.start()
        logger.info(
            "APScheduler initialized and started. Backup scheduled at %s:%s.",
            app.config.get("BACKUP_CRON_HOUR", "3"),
            app.config.get("BACKUP_CRON_MINUTE", "0"),
        )
    except Exception as e:  # pylint: disable=broad-exception-caught # noqa: BLE001
        # Handle cases where scheduler might have started between the check and start()
        if "already running" in str(e).lower():
            logger.debug("APScheduler reported already running during start.")
        else:
            logger.error(f"Failed to initialize APScheduler: {e}")
