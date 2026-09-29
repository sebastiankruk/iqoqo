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
from collections.abc import Callable
from typing import Any

import requests
from celery.result import AsyncResult
from kombu.exceptions import KombuError

from app.core.celery_app import celery
from app.core.s3_service import (
    BUCKET_FEEDBACK,
    S3UploadError,
    get_s3_service,
    warn_if_legacy_rclone_configured,
)

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


@celery.task(bind=True)
def upload_feedback_screenshot(self, local_path: str, filename: str, **kwargs: object) -> None:
    """Uploads a feedback screenshot to the configured feedback bucket.

    Args:
        local_path: Absolute path to the screenshot on local storage.
        filename: Base name to store the object under. Validated as a single
            safe key component, so a caller-supplied value cannot place the
            object outside the ``feedback/`` prefix.

    Raises:
        RuntimeError: if the upload failed. The local file is left in place.
    """
    service = get_s3_service(BUCKET_FEEDBACK)
    if service is None:
        warn_if_legacy_rclone_configured(BUCKET_FEEDBACK)
        logger.info("Feedback object storage not configured, skipping remote upload.")
        return

    try:
        service.upload_file(local_path, service.key_for(filename), content_type="image/jpeg")
        logger.info("Successfully uploaded feedback screenshot %s to remote storage.", filename)
    except (ValueError, S3UploadError) as exc:
        logger.error("Failed to upload feedback screenshot %s: %s", filename, type(exc).__name__)
        raise RuntimeError("Feedback screenshot upload failed") from exc


@celery.task(name="app.core.tasks.refresh_taxonomies_cache")
def refresh_taxonomies_cache() -> dict[str, Any]:
    """Precomputes and materializes global library taxonomy facet trees into Redis cache."""
    from app.api.taxonomies import extract_taxonomies_data
    from app.core.cache import cache

    data = extract_taxonomies_data(scope="global")
    cache_key = "taxonomies:global:/api/taxonomies?"
    cache.set(cache_key, {"success": True, "data": data}, timeout=3600)
    return {"status": "refreshed", "data": data}


@celery.task(
    bind=True,
    name="app.core.tasks.link_manifestation_lod_task",
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
    soft_time_limit=60,
    time_limit=90,
)
def link_manifestation_lod_task(self, manifestation_id: int) -> dict[str, Any]:
    """Resolve and persist Linked Open Data links for a single manifestation asynchronously."""
    from flask import has_app_context

    if not has_app_context():
        from app.core.celery_app import ContextTask

        with ContextTask.get_app().app_context():
            return self.run(manifestation_id=manifestation_id)

    from app.core.lod_linking_service import get_manifestation_semantic_links_dict, resolve_manifestation_links

    try:
        self.update_state(state="STARTED", meta={"manifestation_id": manifestation_id})
    except (ValueError, AttributeError):
        pass
    links = resolve_manifestation_links(manifestation_id)
    summary = get_manifestation_semantic_links_dict(manifestation_id)
    return {
        "status": "completed",
        "manifestation_id": manifestation_id,
        "resolved_count": len(links),
        "summary": summary,
    }


@celery.task(
    bind=True,
    name="app.core.tasks.batch_link_catalog_lod_task",
    soft_time_limit=300,
    time_limit=360,
)
def batch_link_catalog_lod_task(
    self,
    manifestation_ids: list[int] | None = None,
    unlinked_only: bool = False,
    chunk_size: int = 10,
    throttle_delay: float = 0.5,
) -> dict[str, Any]:
    """Batch reconcile Linked Open Data links for multiple catalog manifestations with chunking and throttling."""
    import time
    from datetime import UTC, datetime

    from flask import has_app_context
    from sqlalchemy import select

    if not has_app_context():
        from app.core.celery_app import ContextTask

        with ContextTask.get_app().app_context():
            return self.run(
                manifestation_ids=manifestation_ids,
                unlinked_only=unlinked_only,
                chunk_size=chunk_size,
                throttle_delay=throttle_delay,
            )

    from app.core.cache import cache
    from app.core.lod_linking_service import resolve_manifestation_links
    from app.db import db
    from app.db.core import Expression, Manifestation, SemanticLink
    from app.db.models import InstanceSettings

    task_id = getattr(self.request, "id", None) if hasattr(self, "request") else None
    if task_id:
        try:
            cache.set("lod:active_task_id", task_id, timeout=86400)
            InstanceSettings.set_value("ACTIVE_LOD_TASK_ID", task_id)
        except Exception:  # pylint: disable=broad-except
            pass

    try:
        if manifestation_ids is None:
            query = select(Manifestation.id)
            if unlinked_only:
                manif_subq = select(1).where(
                    SemanticLink.entity_type == "manifestation",
                    SemanticLink.entity_id == Manifestation.id,
                )
                work_subq = (
                    select(1)
                    .select_from(Expression)
                    .where(
                        Expression.id == Manifestation.expression_id,
                        SemanticLink.entity_type == "work",
                        SemanticLink.entity_id == Expression.work_id,
                    )
                )
                query = query.where(~manif_subq.exists()).where(~work_subq.exists())
            manifestation_ids = list(db.session.execute(query).scalars().all())
        elif unlinked_only and manifestation_ids:
            manif_linked = set(
                db.session.execute(
                    select(SemanticLink.entity_id).where(
                        SemanticLink.entity_type == "manifestation",
                        SemanticLink.entity_id.in_(manifestation_ids),
                    )
                )
                .scalars()
                .all()
            )
            # Also find works linked to these manifestations via expression
            manif_work_map = dict(
                db.session.execute(
                    select(Manifestation.id, Expression.work_id)
                    .join(Expression, Manifestation.expression_id == Expression.id)
                    .where(
                        Manifestation.id.in_(manifestation_ids),
                        Expression.work_id.isnot(None),
                    )
                ).all()
            )
            work_ids = list({w for w in manif_work_map.values() if w})
            linked_work_ids = (
                set(
                    db.session.execute(
                        select(SemanticLink.entity_id).where(
                            SemanticLink.entity_type == "work",
                            SemanticLink.entity_id.in_(work_ids),
                        )
                    )
                    .scalars()
                    .all()
                )
                if work_ids
                else set()
            )
            manifestation_ids = [
                mid for mid in manifestation_ids if mid not in manif_linked and manif_work_map.get(mid) not in linked_work_ids
            ]

        total = len(manifestation_ids)
        counts: dict[str, int] = {"dbpedia": 0, "geonames": 0, "wordnet": 0}
        recent_logs: list[dict[str, Any]] = []

        if total == 0:
            return {
                "status": "completed",
                "total": 0,
                "processed": 0,
                "percentage": 100.0,
                "total_resolved": 0,
                "counts": counts,
                "recent_logs": [],
            }

        try:
            self.update_state(
                state="STARTED",
                meta={
                    "total": total,
                    "processed": 0,
                    "percentage": 0.0,
                    "total_resolved": 0,
                    "counts": counts,
                    "recent_logs": [],
                },
            )
        except (ValueError, AttributeError):
            pass

        processed = 0
        total_resolved = 0

        for i in range(0, total, chunk_size):
            chunk = manifestation_ids[i : i + chunk_size]
            for mid in chunk:
                if task_id and (
                    cache.get(f"lod:cancel_task:{task_id}")
                    or (cache.get("lod:active_task_id") != task_id and InstanceSettings.get_value("ACTIVE_LOD_TASK_ID") != task_id)
                ):
                    logger.info("Batch LOD reconciliation task %s cancelled by user request", task_id)
                    percentage = round((processed / total) * 100, 1) if total > 0 else 0.0
                    try:
                        self.update_state(
                            state="REVOKED",
                            meta={
                                "total": total,
                                "processed": processed,
                                "percentage": percentage,
                                "total_resolved": total_resolved,
                                "counts": counts,
                                "recent_logs": list(recent_logs),
                            },
                        )
                    except (ValueError, AttributeError):
                        pass
                    return {
                        "status": "cancelled",
                        "total": total,
                        "processed": processed,
                        "percentage": percentage,
                        "total_resolved": total_resolved,
                        "counts": counts,
                        "recent_logs": list(recent_logs),
                    }

                item_title = f"Manifestation #{mid}"
                try:
                    manif = db.session.get(Manifestation, mid)
                    if manif and manif.title:
                        item_title = manif.title
                except Exception:  # pylint: disable=broad-except
                    pass

                try:
                    links = resolve_manifestation_links(mid)
                    total_resolved += len(links)
                    for link in links:
                        auth = (link.authority or "").lower()
                        counts[auth] = counts.get(auth, 0) + 1

                    log_entry = {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "manifestation_id": mid,
                        "title": item_title,
                        "status": "success" if links else "skipped",
                        "links_added": len(links),
                        "authorities": list({link.authority for link in links}),
                        "error": None,
                    }
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning("Batch LOD resolution failed for manifestation %d: %s", mid, exc)
                    log_entry = {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "manifestation_id": mid,
                        "title": item_title,
                        "status": "error",
                        "links_added": 0,
                        "authorities": [],
                        "error": str(exc),
                    }

                processed += 1
                recent_logs.append(log_entry)
                if len(recent_logs) > 50:
                    recent_logs.pop(0)

                percentage = round((processed / total) * 100, 1)
                try:
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "total": total,
                            "processed": processed,
                            "percentage": percentage,
                            "total_resolved": total_resolved,
                            "counts": counts,
                            "recent_logs": list(recent_logs),
                        },
                    )
                except (ValueError, AttributeError):
                    pass

            if i + chunk_size < total and throttle_delay > 0:
                time.sleep(throttle_delay)

        return {
            "status": "completed",
            "total": total,
            "processed": processed,
            "percentage": 100.0,
            "total_resolved": total_resolved,
            "counts": counts,
            "recent_logs": list(recent_logs),
        }
    finally:
        if task_id:
            try:
                if cache.get("lod:active_task_id") == task_id:
                    cache.delete("lod:active_task_id")
                if InstanceSettings.get_value("ACTIVE_LOD_TASK_ID") == task_id:
                    InstanceSettings.set_value("ACTIVE_LOD_TASK_ID", None)
            except Exception:  # pylint: disable=broad-except
                pass
