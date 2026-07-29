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

"""Tests for Expression.kind mutation via the admin API and escalation system."""

from app.api.auth import generate_internal_jwt
from app.core import frbr_service
from app.db.models import EscalationRequest, Expression, Permission, Role, User, db


def test_update_expression_kind_set_live_performance(client, admin_headers, app):
    """PUT with {"kind": "live_performance"} updates the Expression's kind."""
    with app.app_context():
        work = frbr_service.create_work(title="Kind Set Work")
        expression = frbr_service.create_expression(work_id=work.id, content_type="audio", language="en")
        expr_id = expression.id

    res = client.put(f"/api/v1/admin/frbr/expression/{expr_id}", json={"kind": "live_performance"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True
    assert res.json["data"]["id"] == expr_id

    with app.app_context():
        updated_expr = db.session.get(Expression, expr_id)
        assert updated_expr.kind == "live_performance"


def test_update_expression_kind_cleared_by_empty_string(client, admin_headers, app):
    """PUT with {"kind": ""} clears the Expression's kind to None (studio/default)."""
    with app.app_context():
        work = frbr_service.create_work(title="Kind Clear Work")
        expression = frbr_service.create_expression(work_id=work.id, content_type="audio", kind="live_performance")
        expr_id = expression.id

    res = client.put(f"/api/v1/admin/frbr/expression/{expr_id}", json={"kind": ""}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_expr = db.session.get(Expression, expr_id)
        assert updated_expr.kind is None


def test_update_expression_kind_preserved_when_absent(client, admin_headers, app):
    """PUT without a "kind" key leaves the Expression's existing kind unchanged."""
    with app.app_context():
        work = frbr_service.create_work(title="Kind Preserve Work")
        expression = frbr_service.create_expression(work_id=work.id, content_type="audio", kind="live_performance")
        expr_id = expression.id

    res = client.put(f"/api/v1/admin/frbr/expression/{expr_id}", json={"language": "pl"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json["success"] is True

    with app.app_context():
        updated_expr = db.session.get(Expression, expr_id)
        assert updated_expr.language == "pl"
        assert updated_expr.kind == "live_performance"


def test_change_type_escalation_passes_validation(client, app):
    """Escalation submission with request_type "change_type" is validated and stored."""
    with app.app_context():
        req_perm = Permission.query.filter_by(name="escalate:request").first()
        if not req_perm:
            req_perm = Permission(name="escalate:request")
            db.session.add(req_perm)

        member_role = Role(name="member_change_type")
        member_role.permissions.append(req_perm)
        db.session.add(member_role)

        member = User(email="member_change_type@iqoqo.local", display_name="Member Change Type")
        member.roles.append(member_role)
        db.session.add(member)

        work = frbr_service.create_work(title="Escalation Kind Work")
        expression = frbr_service.create_expression(work_id=work.id, content_type="audio")
        db.session.commit()

        expr_id = expression.id
        headers = {"Authorization": f"Bearer {generate_internal_jwt(member)}"}

    res = client.post(
        f"/api/escalations/expression/{expr_id}",
        json={
            "request_type": "change_type",
            "field_name": "type",
            "current_value": "audio",
            "suggested_value": "video",
            "note": "This release is a video, not audio",
        },
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json["success"] is True
    assert res.json["data"]["request_type"] == "change_type"
    assert res.json["data"]["status"] == "pending"

    with app.app_context():
        stored = db.session.get(EscalationRequest, res.json["data"]["id"])
        assert stored is not None
        assert stored.request_type == "change_type"
        assert stored.expression_id == expr_id
        assert stored.status == "pending"


def test_update_expression_invalid_kind_returns_error(client, admin_headers, app):
    """PUT with an invalid kind value returns an error listing the valid values."""
    with app.app_context():
        work = frbr_service.create_work(title="Kind Invalid Work")
        expression = frbr_service.create_expression(work_id=work.id, content_type="audio")
        expr_id = expression.id

    res = client.put(f"/api/v1/admin/frbr/expression/{expr_id}", json={"kind": "not_a_valid_kind"}, headers=admin_headers)
    assert res.status_code in (400, 404)
    assert res.json["success"] is False
    assert "live_performance" in res.json["error"]

    with app.app_context():
        unchanged_expr = db.session.get(Expression, expr_id)
        assert unchanged_expr.kind is None
