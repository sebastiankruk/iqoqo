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
from sqlalchemy import select

from app.core.celery_app import celery
from app.core.mail_service import MailDeliveryError

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
    name="app.core.tasks.send_account_email_task",
    autoretry_for=(MailDeliveryError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    soft_time_limit=60,
    time_limit=90,
)
def send_account_email_task(self, recipient: str, subject: str, body_text: str) -> dict[str, Any]:
    """Deliver a pre-rendered account-lifecycle email off the request path.

    Used for notices whose send must not be able to affect the outcome of the
    operation that produced them -- above all the post-deletion notice, which is
    sent after the account is already gone.  There, a relay outage has to
    degrade into "the notice arrives late", never into "the deletion is
    reported as failed", so the send is queued and retried rather than awaited.

    Retries cover :class:`~app.core.mail_service.MailDeliveryError` only.  A
    :class:`~app.core.mail_service.MailConfigurationError` is not retried:
    nothing about waiting will make ``MAIL_HOST`` appear, and retrying it would
    burn five attempts and delay the useful log line that names the missing key.

    The body is passed as already-rendered text rather than as a template name,
    so a retry sends exactly what the first attempt would have.  It carries no
    token for the same reason the completion notice does: a queued message
    sitting in Redis is data at rest, and a single-use credential should not
    outlive the request that minted it.

    Args:
        recipient: Destination address.
        subject: Rendered subject line.
        body_text: Rendered ``text/plain`` body.

    Returns:
        A summary dict, safe to inspect in the task result backend.
    """
    from app.core.mail_service import get_mail_service

    get_mail_service().send(recipient=recipient, subject=subject, body_text=body_text)
    return {"status": "sent", "subject": subject}


@celery.task(name="app.core.tasks.purge_expired_account_tokens")
def purge_expired_account_tokens() -> dict[str, Any]:
    """Remove expired account-lifecycle tokens on a schedule.

    Issuance already purges, so this is belt-and-braces for an instance where
    nobody ever requests a second token.  Kept as a task rather than an
    APScheduler job so it runs on the worker that already has the database
    connections, instead of on a scheduler thread that has to open its own.
    """
    from app.core.account_lifecycle import purge_expired_tokens

    removed = purge_expired_tokens()
    if removed:
        logger.info("Purged %d expired account-lifecycle token(s)", removed)
    return {"status": "purged", "removed": removed}


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
                    SemanticLink.status == "accepted",
                )
                work_subq = (
                    select(1)
                    .select_from(Expression)
                    .where(
                        Expression.id == Manifestation.expression_id,
                        SemanticLink.entity_type == "work",
                        SemanticLink.entity_id == Expression.work_id,
                        SemanticLink.status == "accepted",
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
                        SemanticLink.status == "accepted",
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
                            SemanticLink.status == "accepted",
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
                # Check for cancellation: only cancel if explicitly requested for this task
                # or if another task has been explicitly activated in cache or DB.
                is_cancelled = False
                if task_id:
                    if cache.get(f"lod:cancel_task:{task_id}"):
                        is_cancelled = True
                    else:
                        active_cache = cache.get("lod:active_task_id")
                        active_db = InstanceSettings.get_value("ACTIVE_LOD_TASK_ID")
                        if (active_cache and str(active_cache) != str(task_id)) or (active_db and str(active_db) != str(task_id)):
                            is_cancelled = True

                if is_cancelled:
                    logger.info("Batch LOD reconciliation task %s cancelled by user request", task_id)
                    percentage = round((processed / total) * 100, 1) if total > 0 else 0.0
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
                    is_fast = throttle_delay <= 0.2
                    links = resolve_manifestation_links(mid, fast_mode=is_fast)
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


@celery.task(
    name="app.core.tasks.cleanup_lod_links_task",
    soft_time_limit=300,
    time_limit=360,
)
def cleanup_lod_links_task(dry_run: bool = True, batch_size: int = 100) -> dict[str, Any]:
    """Re-score existing accepted SemanticLinks and demote sub-threshold links to suggested.

    In dry-run mode, calculates potential demotions without mutating database rows.
    In apply mode (dry_run=False), updates link.status to 'suggested' and writes to EntityAuditLog.
    """
    from flask import has_app_context

    if not has_app_context():
        from app.core.celery_app import ContextTask

        with ContextTask.get_app().app_context():
            return cleanup_lod_links_task(dry_run=dry_run, batch_size=batch_size)

    from app.core.config_service import ConfigService
    from app.core.lod_linking_service import compute_composite_score, is_disambiguation
    from app.db import db
    from app.db.core import EntityAuditLog, Manifestation, SemanticLink, Work

    auto_threshold = ConfigService.get_float("LOD_AUTO_APPLY_THRESHOLD", 0.82)
    suggestion_threshold = ConfigService.get_float("LOD_SUGGESTION_THRESHOLD", 0.55)

    links = db.session.execute(select(SemanticLink).where(SemanticLink.status == "accepted")).scalars().all()

    total_evaluated = len(links)
    demoted_count = 0
    rejected_count = 0
    unchanged_count = 0
    demotions: list[dict[str, Any]] = []

    for link in links:
        target_title = ""
        author: str | None = None
        year: int | None = None

        if link.entity_type == "work":
            work = db.session.get(Work, link.entity_id)
            if work:
                target_title = work.title or ""
                if work.meta and isinstance(work.meta.get("authors"), list):
                    authors = [a for a in work.meta["authors"] if isinstance(a, str)]
                    if authors:
                        author = authors[0]
        elif link.entity_type == "manifestation":
            manif = db.session.get(Manifestation, link.entity_id)
            if manif:
                target_title = manif.title or ""
                author = manif.author
                if manif.publication_date:
                    year = manif.publication_date.year

        cand_comment = (link.attributes or {}).get("comment", "")
        cand_label = link.pref_label or ""

        new_score = compute_composite_score(
            candidate_label=cand_label,
            target_title=target_title or cand_label,
            author=author,
            candidate_comment=cand_comment,
            year=year,
            rank_margin=0.5,
            has_class_match=True,
        )

        effective_score = max(new_score, link.confidence if link.confidence is not None else 0.0)

        if effective_score < suggestion_threshold or is_disambiguation(link.external_uri, cand_label, cand_comment):
            rejected_count += 1
            demoted_count += 1
            demotions.append(
                {
                    "link_id": link.id,
                    "authority": link.authority,
                    "external_uri": link.external_uri,
                    "old_score": link.confidence,
                    "new_score": effective_score,
                    "new_status": "suggested",
                }
            )
            if not dry_run:
                link.status = "suggested"
                audit = EntityAuditLog(
                    entity_type=link.entity_type,
                    entity_id=link.entity_id,
                    actor_id=None,
                    change_type="semantic_link_demoted",
                    diff={
                        "link_id": link.id,
                        "authority": link.authority,
                        "external_uri": link.external_uri,
                        "old_status": "accepted",
                        "new_status": "suggested",
                        "score": effective_score,
                    },
                )
                db.session.add(audit)
        elif effective_score < auto_threshold:
            demoted_count += 1
            demotions.append(
                {
                    "link_id": link.id,
                    "authority": link.authority,
                    "external_uri": link.external_uri,
                    "old_score": link.confidence,
                    "new_score": effective_score,
                    "new_status": "suggested",
                }
            )
            if not dry_run:
                link.status = "suggested"
                audit = EntityAuditLog(
                    entity_type=link.entity_type,
                    entity_id=link.entity_id,
                    actor_id=None,
                    change_type="semantic_link_demoted",
                    diff={
                        "link_id": link.id,
                        "authority": link.authority,
                        "external_uri": link.external_uri,
                        "old_status": "accepted",
                        "new_status": "suggested",
                        "score": effective_score,
                    },
                )
                db.session.add(audit)
        else:
            unchanged_count += 1

    if not dry_run and demoted_count > 0:
        db.session.commit()

    return {
        "dry_run": dry_run,
        "total_evaluated": total_evaluated,
        "demoted": demoted_count,
        "rejected": rejected_count,
        "unchanged": unchanged_count,
        "sample_demotions": demotions[:20],
    }
