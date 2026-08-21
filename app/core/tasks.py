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
"""Centralized task management using Celery.

Preserves the public API (submit_task, get_task_result) while using
Redis as a distributed broker to support multi-process Gunicorn scaling.
"""

import logging
import os
import subprocess
from collections.abc import Callable

from celery.result import AsyncResult
from kombu.exceptions import KombuError

from app.config import Config
from app.core.celery_app import celery
from app.utils.rclone_utils import get_rclone_target

logger = logging.getLogger(__name__)


# Legacy mapping for task status consistency
# Celery -> iqoqo
STATUS_MAP = {
    "PENDING": "pending",
    "STARTED": "processing",
    "RETRY": "processing",
    "SUCCESS": "completed",
    "FAILURE": "failed",
}


@celery.task(bind=True)
def _task_wrapper(self, func_path: str, *args, user_id=None, **kwargs):
    """Wraps target functions for Celery execution.

    Args:
        func_path: Full dotted path to the function to execute (e.g. 'app.utils.vision.extract_metadata')
    """
    # Import function dynamically to avoid circular dependencies in worker
    import importlib

    module_path, func_name = func_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)

    # Store user_id in task metadata for ownership verification
    self.update_state(state="STARTED", meta={"user_id": user_id})

    try:
        result = func(*args, **kwargs)
        return {"result": result, "user_id": user_id}
    except Exception as e:
        logger.exception(f"Task {self.request.id} failed")
        raise e


def submit_task(func: Callable, *args, user_id: str | None = None, **kwargs) -> str | None:
    """
    Submit a background task to the Celery queue.

    Args:
        func: The callable to execute in the background.
        *args, **kwargs: Arguments to pass to the callable.
        user_id: Optional user ID for ownership tracking.

    Returns:
        str | None: A unique task_id to poll for the result, or None if the queue
            is unavailable (e.g. Redis is down). Callers must handle None gracefully.
    """
    # Convert function to dotted path for Celery serialization
    func_path = f"{func.__module__}.{func.__name__}"
    try:
        # retry=False prevents blocking the gunicorn worker for ~20 s when Redis is
        # unreachable (Celery default: 20 retries × 1 s each before raising).
        result = _task_wrapper.apply_async(
            args=(func_path,) + tuple(args),
            kwargs={"user_id": user_id, **kwargs},
            retry=False,
        )
        return str(result.id)
    except (KombuError, OSError) as exc:
        logger.warning("Background task queue unavailable for %s: %s", func.__name__, exc)
        return None


def get_task_result(task_id: str, user_id: str | None = None) -> dict | None:
    """
    Retrieve the current status or result of a background task from Redis.

    Args:
        task_id: The task ID to retrieve.
        user_id: Optional user ID to verify ownership.

    Returns:
        dict | None: Task result if found and owned by user, None otherwise.
    """
    res = AsyncResult(task_id, app=celery)

    # Basic state mapping
    status = STATUS_MAP.get(res.state, "pending")

    # In Celery, result can contain either the return value (on success)
    # or the exception (on failure), or custom meta (if STARTED).
    result_val = res.result

    # Ownership check
    task_user_id = None
    actual_result = None
    error_msg = None

    if res.state == "STARTED":
        task_user_id = result_val.get("user_id") if isinstance(result_val, dict) else None
    elif res.state == "SUCCESS":
        task_user_id = result_val.get("user_id") if isinstance(result_val, dict) else None
        actual_result = result_val.get("result") if isinstance(result_val, dict) else result_val
    elif res.state == "FAILURE":
        # Failure result is usually the Exception object
        error_msg = str(result_val)
        # We might not have ownership info here if it failed early,
        # but the worker tries to store it in update_state before failure
        if hasattr(res, "info") and isinstance(res.info, dict):
            task_user_id = res.info.get("user_id")

    # Verify ownership if user_id is provided
    if user_id and task_user_id:
        if str(task_user_id) != str(user_id):
            return None

    # Construct response matching legacy iqoqo format
    output = {"status": status, "user_id": task_user_id}
    if res.state == "SUCCESS":
        output["result"] = actual_result
    elif actual_result is not None:
        output["result"] = actual_result

    if error_msg:
        output["error"] = error_msg

    return output


def shutdown_executor() -> None:
    """No-op for Celery migration."""
    pass


class BackupManager:
    """Helper class to manage backups in local storage and remote cloud via rclone."""

    def __init__(self, backup_dir: str = "/data/backups", rclone_remote_fast: str | None = None, rclone_remote_archive: str | None = None):
        self.backup_dir = backup_dir
        self.rclone_remote_fast = rclone_remote_fast or getattr(Config, "RCLONE_REMOTE_FAST", "iqoqo-backup")
        self.rclone_remote_archive = rclone_remote_archive or getattr(Config, "RCLONE_REMOTE_ARCHIVE", "iqoqo-glacier")

    def list_backups(self) -> list[str]:
        """Mockable method to list backups."""
        if not os.path.exists(self.backup_dir):
            return []
        return [f for f in os.listdir(self.backup_dir) if os.path.isfile(os.path.join(self.backup_dir, f))]

    def delete_backup(self, filename: str) -> None:
        """Mockable method to delete a backup from fast storage."""
        file_path = os.path.join(self.backup_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    def upload_to_glacier(self, filename: str) -> None:
        """Uploads a file to long-term storage via rclone proxy."""
        file_path = os.path.join(self.backup_dir, filename)
        try:
            remote_archive = str(self.rclone_remote_archive or "iqoqo-glacier")
            target = get_rclone_target(remote_archive, "archives")
            subprocess.run(["rclone", "copy", "--s3-no-check-bucket", "--", file_path, target], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error("rclone upload failed: %s", e.stderr)
            raise RuntimeError(f"Backup sync failed: {e.stderr}") from e


@celery.task(bind=True)
def rotate_and_archive_backups(self) -> None:
    """
    Automated Backup Retention Task.
    Enforces 7 daily and 5 weekly backups in fast storage (Dropbox).
    Archives older backups to AWS S3 Glacier and removes them from fast storage.
    """
    manager = BackupManager()
    backups = manager.list_backups()

    # Sort backups by modification time (newest first)
    def get_mtime(filename: str) -> float:
        return os.path.getmtime(os.path.join(manager.backup_dir, filename))

    backups.sort(key=get_mtime, reverse=True)

    for i, backup in enumerate(backups):
        # Keep 7 daily + 5 weekly = 12 newest backups in fast storage
        if i < 12:
            continue

        # Archive older backups
        try:
            manager.upload_to_glacier(backup)
            manager.delete_backup(backup)
            logger.info("Archived %s to Glacier and removed from local storage.", backup)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to archive %s: %s", backup, e)


@celery.task(bind=True)
def upload_feedback_screenshot(self, local_path: str, filename: str, **kwargs: object) -> None:
    """Uploads a feedback screenshot via rclone to RCLONE_FEEDBACK_REMOTE."""
    rclone_remote = getattr(Config, "RCLONE_FEEDBACK_REMOTE", None) or os.environ.get("RCLONE_FEEDBACK_REMOTE")
    if not rclone_remote:
        logger.info("RCLONE_FEEDBACK_REMOTE not configured, skipping remote upload.")
        return

    try:
        target = get_rclone_target(rclone_remote, "feedback", filename)
        subprocess.run(["rclone", "copyto", "--", local_path, target], check=True, capture_output=True, text=True)
        logger.info("Successfully uploaded feedback screenshot %s to rclone remote.", filename)
    except subprocess.CalledProcessError as e:
        logger.error("rclone copyto failed for feedback screenshot %s: %s", filename, e.stderr)
        raise RuntimeError(f"Feedback screenshot upload failed: {e.stderr}") from e
