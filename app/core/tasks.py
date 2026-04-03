"""Centralized task management using ThreadPoolExecutor."""

# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import atexit
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Centralized managed thread pool for the entire application.
# Replaces unmanaged threading.Thread instances to prevent memory exhaustion.
# Defaults to a reasonable number of workers to prevent system overload.
global_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="iqoqo_worker")


def shutdown_executor():
    """Gracefully shuts down the global ThreadPoolExecutor on exit."""
    logger.info("Shutting down global ThreadPoolExecutor...")
    global_executor.shutdown(wait=False)


atexit.register(shutdown_executor)


def submit_task(func, *args, **kwargs):
    """
    Submit a background task to the centralized thread pool.

    Args:
        func: The callable to execute in the background.
        *args, **kwargs: Arguments to pass to the callable.

    Returns:
        Future object representing the execution of the callable.
    """
    return global_executor.submit(func, *args, **kwargs)
