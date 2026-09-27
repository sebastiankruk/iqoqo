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
"""Tests for LOD administrative reconciliation REST endpoints and access control."""

from unittest.mock import MagicMock, patch

from app.db import db
from app.db.core import Expression, Manifestation, SemanticLink, Work
from app.db.models import Role, User


def _create_user_with_role(email: str, role_name: str | None = None) -> User:
    """Helper to create and persist a test user with a specific role."""
    user = User(email=email, google_id=f"google:{email}", is_active=True)
    if role_name:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name)
            db.session.add(role)
            db.session.flush()
        user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    return user


def test_lod_reconcile_access_control(app, client):
    """Test POST /api/v1/admin/lod/reconcile role-based access control (Admin & Custodian allowed, Collector rejected)."""
    with app.app_context():
        admin_user = _create_user_with_role("admin_test@iqoqo.org", "admin")
        custodian_user = _create_user_with_role("custodian_test@iqoqo.org", "custodian")
        collector_user = _create_user_with_role("collector_test@iqoqo.org", None)

        with patch("app.core.tasks.batch_link_catalog_lod_task.delay") as mock_delay:
            mock_task = MagicMock()
            mock_task.id = "mock-task-uuid-123"
            mock_delay.return_value = mock_task

            # 1. Unauthenticated -> 401
            resp_unauth = client.post("/api/v1/admin/lod/reconcile", json={"unlinked_only": True})
            assert resp_unauth.status_code == 401

            # 2. Standard collector -> 403 Forbidden
            with (
                patch("jwt.decode", return_value={"sub": str(collector_user.id), "jti": "jti1", "exp": 9999999999}),
                patch("app.api.decorators._is_token_revoked", return_value=False),
            ):
                resp_collector = client.post(
                    "/api/v1/admin/lod/reconcile",
                    json={"unlinked_only": True},
                    headers={"Authorization": "Bearer mock-token"},
                )
                assert resp_collector.status_code == 403

            # 3. Admin user -> 202 Accepted
            with (
                patch("jwt.decode", return_value={"sub": str(admin_user.id), "jti": "jti2", "exp": 9999999999}),
                patch("app.api.decorators._is_token_revoked", return_value=False),
            ):
                resp_admin = client.post(
                    "/api/v1/admin/lod/reconcile",
                    json={"unlinked_only": True, "throttle_delay": 0.1},
                    headers={"Authorization": "Bearer mock-token"},
                )
                assert resp_admin.status_code == 202
                data = resp_admin.get_json()
                assert data["success"] is True
                assert data["data"]["task_id"] == "mock-task-uuid-123"

            # 4. Custodian user -> 202 Accepted
            with (
                patch("jwt.decode", return_value={"sub": str(custodian_user.id), "jti": "jti3", "exp": 9999999999}),
                patch("app.api.decorators._is_token_revoked", return_value=False),
            ):
                resp_custodian = client.post(
                    "/api/v1/admin/lod/reconcile",
                    json={"unlinked_only": False},
                    headers={"Authorization": "Bearer mock-token"},
                )
                assert resp_custodian.status_code == 202
                data = resp_custodian.get_json()
                assert data["success"] is True


def test_lod_task_status_polling(app, client):
    """Test GET /api/v1/admin/lod/tasks/<task_id> returns progress metadata."""
    with app.app_context():
        custodian_user = _create_user_with_role("custodian_poll@iqoqo.org", "custodian")

        with patch("celery.result.AsyncResult") as mock_async_result:
            # Active task state: PROGRESS
            mock_task = MagicMock()
            mock_task.state = "PROGRESS"
            mock_task.info = {
                "total": 100,
                "processed": 45,
                "percentage": 45.0,
                "total_resolved": 88,
                "counts": {"dbpedia": 40, "geonames": 30, "wordnet": 18},
                "recent_logs": [
                    {
                        "timestamp": "2026-09-27T10:00:00Z",
                        "manifestation_id": 1,
                        "title": "Dune",
                        "status": "success",
                        "links_added": 2,
                    }
                ],
            }
            mock_async_result.return_value = mock_task

            with (
                patch("jwt.decode", return_value={"sub": str(custodian_user.id), "jti": "jti4", "exp": 9999999999}),
                patch("app.api.decorators._is_token_revoked", return_value=False),
            ):
                resp = client.get(
                    "/api/v1/admin/lod/tasks/test-task-progress",
                    headers={"Authorization": "Bearer mock-token"},
                )
                assert resp.status_code == 200
                data = resp.get_json()
                assert data["success"] is True
                assert data["data"]["status"] == "processing"
                assert data["data"]["percentage"] == 45.0
                assert data["data"]["counts"]["dbpedia"] == 40
                assert len(data["data"]["recent_logs"]) == 1


def test_lod_stats_aggregation(app, client):
    """Test GET /api/v1/admin/lod/stats aggregates database semantic links correctly."""
    with app.app_context():
        admin_user = _create_user_with_role("admin_stats@iqoqo.org", "admin")

        work = Work(title="Solaris")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="pl")
        db.session.add(expr)
        db.session.flush()

        m1 = Manifestation(expression_id=expr.id, isbn13="9788308000001")
        m2 = Manifestation(expression_id=expr.id, isbn13="9788308000002")
        db.session.add_all([m1, m2])
        db.session.flush()

        # Add semantic links to m1
        sl_db = SemanticLink(
            entity_type="manifestation",
            entity_id=m1.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Solaris",
        )
        sl_geo = SemanticLink(
            entity_type="manifestation",
            entity_id=m1.id,
            authority="geonames",
            external_uri="https://sws.geonames.org/756135/",
        )
        db.session.add_all([sl_db, sl_geo])
        db.session.commit()

        with (
            patch("jwt.decode", return_value={"sub": str(admin_user.id), "jti": "jti5", "exp": 9999999999}),
            patch("app.api.decorators._is_token_revoked", return_value=False),
        ):
            resp = client.get(
                "/api/v1/admin/lod/stats",
                headers={"Authorization": "Bearer mock-token"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            stats = data["data"]
            assert stats["total_manifestations"] >= 2
            assert stats["linked_manifestations"] >= 1
            assert stats["by_authority"]["dbpedia"] >= 1
            assert stats["by_authority"]["geonames"] >= 1
            assert stats["total_links"] >= 2
