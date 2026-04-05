"""Centralized task management using ThreadPoolExecutor."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import atexit
import logging
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
_task_results: dict = {}

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
    _task_results[task_id] = {"status": "processing"}
    try:
        if app is not None:
            with app.app_context():
                result = func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        _task_results[task_id] = {"status": "completed", "result": result}
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Task {task_id} failed")
        _task_results[task_id] = {"status": "failed", "error": str(e)}


def submit_task(func: Callable, *args, **kwargs) -> str:
    """
    Submit a background task to the centralized thread pool.

    The current Flask application context (if any) is captured at submission
    time and replayed inside the worker thread, ensuring that SQLAlchemy
    sessions and Flask config are available to the task function.

    Args:
        func: The callable to execute in the background.
        *args, **kwargs: Arguments to pass to the callable.

    Returns:
        str: A unique task_id to poll for the result.
    """
    task_id = str(uuid.uuid4())
    _task_results[task_id] = {"status": "pending"}
    app = _get_flask_app()
    global_executor.submit(_task_wrapper, task_id, app, func, *args, **kwargs)
    return task_id


def get_task_result(task_id: str) -> dict | None:
    """
    Retrieve the current status or result of a background task.
    """
    return _task_results.get(task_id)
