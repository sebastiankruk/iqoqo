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
from unittest.mock import MagicMock, patch

from app.core.tasks import get_task_result, submit_task


def dummy_task(x, y):
    return x + y


def failing_task():
    raise ValueError("Task failed spectacularly")


# Celery eager mode is handled globally in conftest.py


def test_submit_task_returns_id():
    task_id = submit_task(dummy_task, 10, 20)
    assert isinstance(task_id, str)
    assert len(task_id) > 0


def test_get_task_result_success():
    task_id = submit_task(dummy_task, 1, 2)
    result = get_task_result(task_id)
    assert result is not None
    assert result["status"] == "completed"
    assert result["result"] == 3


def test_get_task_result_failure():
    task_id = submit_task(failing_task)
    result = get_task_result(task_id)
    assert result is not None
    assert result["status"] == "failed"
    assert "Task failed spectacularly" in result["error"]


def test_get_task_result_user_isolation():
    task_id = submit_task(dummy_task, 5, 5, user_id="user_a")

    # Poll as user_a -> should work
    result_a = get_task_result(task_id, user_id="user_a")
    assert result_a is not None
    assert result_a["result"] == 10

    # Poll as user_b -> should return None (isolated)
    result_b = get_task_result(task_id, user_id="user_b")
    assert result_b is None


def test_get_task_result_not_found():
    result = get_task_result("non_existent_id")
    # Celery PENDING state for non-existent tasks by default
    assert result["status"] == "pending"


def test_batch_link_catalog_lod_task_metrics_and_logs(app):
    """Test batch_link_catalog_lod_task counts per authority and ring-buffers recent logs."""
    from app.core.tasks import batch_link_catalog_lod_task
    from app.db.core import SemanticLink

    with app.app_context():
        manifestation_ids = [101, 102]

        link_dbpedia = MagicMock(spec=SemanticLink, authority="dbpedia")
        link_geonames = MagicMock(spec=SemanticLink, authority="geonames")

        def mock_resolve(mid, *args, **kwargs):
            if mid == 101:
                return [link_dbpedia, link_geonames]
            return []

        with (
            patch.object(batch_link_catalog_lod_task, "update_state") as mock_update,
            patch("app.core.lod_linking_service.resolve_manifestation_links", side_effect=mock_resolve),
        ):
            res = batch_link_catalog_lod_task(manifestation_ids, chunk_size=1, throttle_delay=0.0)

            assert res["status"] == "completed"
            assert res["total"] == 2
            assert res["processed"] == 2
            assert res["percentage"] == 100.0
            assert res["total_resolved"] == 2
            assert res["counts"]["dbpedia"] == 1
            assert res["counts"]["geonames"] == 1
            assert res["counts"]["wordnet"] == 0
            assert len(res["recent_logs"]) == 2
            assert res["recent_logs"][0]["status"] == "success"
            assert res["recent_logs"][0]["links_added"] == 2
            assert res["recent_logs"][1]["status"] == "skipped"
            assert res["recent_logs"][1]["links_added"] == 0
            assert mock_update.called


def test_batch_link_catalog_lod_task_unlinked_only(app):
    """Test batch_link_catalog_lod_task filtering with unlinked_only=True."""
    from app.core.tasks import batch_link_catalog_lod_task
    from app.db import db
    from app.db.core import Expression, Manifestation, SemanticLink, Work

    with app.app_context():
        work = Work(title="Test Book")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        m1 = Manifestation(expression_id=expr.id, isbn13="9780000000001")
        m2 = Manifestation(expression_id=expr.id, isbn13="9780000000002")
        db.session.add_all([m1, m2])
        db.session.flush()

        # m1 is already linked
        sl = SemanticLink(
            entity_type="manifestation",
            entity_id=m1.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Test",
        )
        db.session.add(sl)
        db.session.commit()

        with (
            patch.object(batch_link_catalog_lod_task, "update_state"),
            patch("app.core.lod_linking_service.resolve_manifestation_links", return_value=[]) as mock_resolve,
        ):
            res = batch_link_catalog_lod_task(
                manifestation_ids=[m1.id, m2.id],
                unlinked_only=True,
                chunk_size=10,
                throttle_delay=0.0,
            )

            assert res["total"] == 1
            assert res["processed"] == 1
            mock_resolve.assert_called_once_with(m2.id, fast_mode=True)


def test_context_task_auto_app_context():
    """Verify that Celery tasks automatically bind a Flask app context when executed outside one."""
    import threading

    from flask import has_app_context

    from app.core.celery_app import celery

    result_holder = {}

    @celery.task(bind=True)
    def task_needing_context(self):
        from flask import current_app, has_app_context

        from app.db import db

        return {
            "has_context": has_app_context(),
            "app_name": current_app.name,
            "session_active": db.session is not None,
        }

    def run_in_thread():
        result_holder["thread_had_context"] = has_app_context()
        result_holder["task_result"] = task_needing_context()

    t = threading.Thread(target=run_in_thread)
    t.start()
    t.join()

    assert result_holder["thread_had_context"] is False
    assert result_holder["task_result"]["has_context"] is True
    assert result_holder["task_result"]["app_name"] == "app"
    assert result_holder["task_result"]["session_active"] is True


def test_batch_link_catalog_lod_task_cancellation_resilience(app):
    """Test batch_link_catalog_lod_task cancellation logic and verify empty DB settings don't abort."""
    from unittest.mock import MagicMock

    from app.core.cache import cache
    from app.core.tasks import batch_link_catalog_lod_task
    from app.db.models import InstanceSettings

    with app.app_context():
        manifestation_ids = [101, 102, 103, 104]

        # 1. Verify empty DB setting / cache does NOT falsely trigger cancellation
        cache.delete("lod:active_task_id")
        InstanceSettings.set_value("ACTIVE_LOD_TASK_ID", None)

        batch_link_catalog_lod_task.push_request(id="task-safe-123")
        try:
            with (
                patch.object(batch_link_catalog_lod_task, "update_state"),
                patch("app.core.lod_linking_service.resolve_manifestation_links", return_value=[]),
            ):
                res = batch_link_catalog_lod_task(manifestation_ids, chunk_size=2, throttle_delay=0.0)
                assert res["status"] == "completed"
                assert res["processed"] == 4
        finally:
            batch_link_catalog_lod_task.pop_request()

        # 2. Verify explicit cancellation via lod:cancel_task triggers clean cancellation
        cache.set("lod:cancel_task:task-cancel-456", True, timeout=60)
        batch_link_catalog_lod_task.push_request(id="task-cancel-456")
        try:
            with (
                patch.object(batch_link_catalog_lod_task, "update_state"),
                patch("app.core.lod_linking_service.resolve_manifestation_links", return_value=[]),
            ):
                res_cancelled = batch_link_catalog_lod_task(manifestation_ids, chunk_size=2, throttle_delay=0.0)
                assert res_cancelled["status"] == "cancelled"
                assert res_cancelled["processed"] == 0
        finally:
            batch_link_catalog_lod_task.pop_request()
