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
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""Celery application factory and Flask integration helpers."""

import logging
import os

from celery import Celery, Task
from celery.signals import worker_process_init

# Suppress highly verbose urllib3 connectionpool logs at DEBUG level (caused by OTel exporter POSTs)
logging.getLogger("urllib3").setLevel(logging.WARNING)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class ContextTask(Task):  # type: ignore[misc]
    """Celery task that automatically ensures an active Flask application context."""

    _flask_app = None

    @classmethod
    def get_app(cls):
        """Retrieve existing Flask app or create a new one on demand."""
        from flask import current_app, has_app_context

        if has_app_context():
            return current_app
        if cls._flask_app is None:
            from app import create_app

            cls._flask_app = create_app()
        return cls._flask_app

    def __call__(self, *args, **kwargs):
        """Execute task inside an active Flask application context."""
        from flask import has_app_context

        if has_app_context():
            return self.run(*args, **kwargs)
        with self.get_app().app_context():
            return self.run(*args, **kwargs)


celery: Celery = Celery(
    "iqoqo",
    broker=REDIS_URL,
    backend=REDIS_URL,
    task_cls=ContextTask,
    include=["app.core.tasks"],
)
celery.Task = ContextTask

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,  # 1-hour TTL matching old _TASK_TTL_SECONDS
    broker_connection_retry_on_startup=True,
    task_time_limit=600,  # hard kill after 10 min (covers slowest LLM tier at 300s)
    task_soft_time_limit=540,  # SoftTimeLimitExceeded after 9 min for graceful cleanup
    beat_schedule={
        "refresh-taxonomies-hourly": {
            "task": "app.core.tasks.refresh_taxonomies_cache",
            "schedule": 3600.0,
        },
    },
)


def init_celery(app) -> None:
    """Bind Flask app context to Celery tasks."""
    ContextTask._flask_app = app


@worker_process_init.connect
def _dispose_db_connections(**kwargs) -> None:
    """Dispose inherited DB connections after fork to prevent socket corruption."""
    try:
        from app.db import db

        if db.engine:
            db.engine.dispose()
    except (AttributeError, ValueError, RuntimeError):
        pass  # Worker context or DB might not be fully ready yet
