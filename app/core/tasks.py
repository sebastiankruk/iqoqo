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
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Centralized managed thread pool for the entire application.
# Replaces unmanaged threading.Thread instances to prevent memory exhaustion.
# Defaults to a reasonable number of workers to prevent system overload.
global_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="iqoqo_worker")

# In-memory store for tracking async task status and results
_task_results = {}


def shutdown_executor():
    """Gracefully shuts down the global ThreadPoolExecutor on exit."""
    logger.info("Shutting down global ThreadPoolExecutor...")
    global_executor.shutdown(wait=False)


atexit.register(shutdown_executor)


def _task_wrapper(task_id: str, func, *args, **kwargs):
    """Wraps the target function to record its outcome."""
    _task_results[task_id] = {"status": "processing"}
    try:
        result = func(*args, **kwargs)
        _task_results[task_id] = {"status": "completed", "result": result}
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Task {task_id} failed")
        _task_results[task_id] = {"status": "failed", "error": str(e)}


def submit_task(func, *args, **kwargs) -> str:
    """
    Submit a background task to the centralized thread pool.

    Args:
        func: The callable to execute in the background.
        *args, **kwargs: Arguments to pass to the callable.

    Returns:
        str: A unique task_id to poll for the result.
    """
    task_id = str(uuid.uuid4())
    _task_results[task_id] = {"status": "pending"}
    global_executor.submit(_task_wrapper, task_id, func, *args, **kwargs)
    return task_id


def get_task_result(task_id: str) -> dict | None:
    """
    Retrieve the current status or result of a background task.
    """
    return _task_results.get(task_id)
