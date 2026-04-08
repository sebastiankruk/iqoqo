"""Centralized task management using ThreadPoolExecutor."""

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

import atexit
import logging
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)

# Centralized managed thread pool for the entire application.
# Replaces unmanaged threading.Thread instances to prevent memory exhaustion.
# Defaults to a reasonable number of workers to prevent system overload.
global_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="iqoqo_worker")

# In-memory store for tracking async task status and results
# Protected by lock for thread-safe access
_task_results: dict = {}
_task_lock = threading.Lock()

# TTL for task results: 1 hour
_TASK_TTL_SECONDS = 3600


def _cleanup_old_tasks() -> None:
    """Remove tasks older than TTL to prevent unbounded memory growth."""
    with _task_lock:
        now = time.time()
        expired = [tid for tid, data in _task_results.items() if data.get("_created_at", 0) + _TASK_TTL_SECONDS < now]
        for tid in expired:
            del _task_results[tid]
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired task results")


def _record_task(task_id: str, status: str, **kwargs) -> None:
    """Thread-safe helper to record task status."""
    with _task_lock:
        _task_results[task_id] = {"status": status, "_created_at": time.time(), **kwargs}


# Lazily cached Flask app reference — set on first submit_task call.
# This allows tasks.py to remain import-time free of Flask so it can be
# imported before the app is fully constructed.
_flask_app: "Flask | None" = None


def _get_flask_app() -> "Flask | None":
    """Return the current Flask application if one is running."""
    global _flask_app  # pylint: disable=global-statement
    if _flask_app is not None:
        return _flask_app
    try:
        from flask import current_app  # pylint: disable=import-outside-toplevel

        _flask_app = current_app._get_current_object()  # type: ignore[attr-defined] # pylint: disable=protected-access
    except RuntimeError:
        # No application context (e.g. during tests without app context)
        pass
    return _flask_app


def shutdown_executor() -> None:
    """Gracefully shuts down the global ThreadPoolExecutor on exit."""
    logger.info("Shutting down global ThreadPoolExecutor...")
    global_executor.shutdown(wait=False)


atexit.register(shutdown_executor)


def _task_wrapper(task_id: str, app: "Flask | None", func: Callable, *args, **kwargs) -> None:
    """Wraps the target function to record its outcome.

    Pushes a Flask application context when one is available so that
    database sessions and other Flask-bound resources work correctly
    inside background threads.
    """
    _record_task(task_id, "processing")
    try:
        if app is not None:
            with app.app_context():
                result = func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        _record_task(task_id, "completed", result=result)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Task {task_id} failed")
        _record_task(task_id, "failed", error=str(e))


def submit_task(func: Callable, *args, user_id: str | None = None, **kwargs) -> str:
    """
    Submit a background task to the centralized thread pool.

    The current Flask application context (if any) is captured at submission
    time and replayed inside the worker thread, ensuring that SQLAlchemy
    sessions and Flask config are available to the task function.

    Args:
        func: The callable to execute in the background.
        *args, **kwargs: Arguments to pass to the callable.
        user_id: Optional user ID for ownership tracking.

    Returns:
        str: A unique task_id to poll for the result.
    """
    task_id = str(uuid.uuid4())
    _record_task(task_id, "pending", user_id=user_id)
    app = _get_flask_app()
    global_executor.submit(_task_wrapper, task_id, app, func, *args, **kwargs)
    return task_id


def get_task_result(task_id: str, user_id: str | None = None) -> dict | None:
    """
    Retrieve the current status or result of a background task.
    Thread-safe read with TTL cleanup on access.

    Args:
        task_id: The task ID to retrieve.
        user_id: Optional user ID to verify ownership. If provided and task
                 has a different owner, returns None.

    Returns:
        dict | None: Task result if found and owned by user, None otherwise.
    """
    with _task_lock:
        result = _task_results.get(task_id)
        if result:
            # Verify ownership if user_id provided
            if user_id is not None and result.get("user_id") != user_id:
                return None
            # Create a copy without internal _created_at field
            return {k: v for k, v in result.items() if k != "_created_at"}
        return None
