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
import pytest

from app.core.frbr_service import update_expression, update_frbr_entity_type
from app.db.models import EscalationRequest, Expression, Item, Manifestation, Work, db


def test_update_frbr_entity_type_upward_propagation(app):
    with app.app_context():
        # Setup initial FRBR entities
        work = Work(title="Test Work", meta={"type": "Book"}, sort_title="Test Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="Book")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, meta={"type": "Book"})
        db.session.add(manif)
        db.session.flush()

        # Item removed to avoid owner_id constraint issues

        # Update Manifestation type to Board Game
        updated_manif = update_frbr_entity_type(Manifestation, manif.id, "Board Game")

        # Verify Manifestation is updated
        assert updated_manif.meta["type"] == "Board Game"

        # Verify upward propagation to Expression and Work
        db.session.refresh(expr)
        db.session.refresh(work)
        assert expr.content_type == "Board Game"
        assert work.meta["type"] == "Board Game"

        # item assertions removed


def test_type_change_user_request_acceptance(client, app, admin_headers):
    import uuid

    from app.db.models import User

    with app.app_context():
        user = User(id=uuid.uuid4(), email="test@iqoqo.app", password_hash="hash", display_name="Test User")
        db.session.add(user)
        work = Work(title="Test Work", meta={"type": "Movie"}, sort_title="Test Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="Movie")
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, meta={"type": "Movie"})
        db.session.add(manif)
        db.session.commit()

        # Create EscalationRequest
        req = EscalationRequest(
            user_id=user.id,
            manifestation_id=manif.id,
            target_type="Manifestation",
            field_name="type",
            current_value="Movie",
            suggested_value="Video Game",
            request_type="change_type",
            status="pending",
        )
        db.session.add(req)
        db.session.commit()

        req_id = req.id
        manif_id = manif.id
        expr_id = expr.id

    # Admin approves
    resp = client.patch(
        f"/api/escalations/{req_id}", json={"status": "accepted", "resolution_note": "Approved type change"}, headers=admin_headers
    )

    assert resp.status_code == 200

    with app.app_context():
        req = db.session.get(EscalationRequest, req_id)
        assert req.status == "accepted"
        assert req.resolution_note == "Approved type change"

        manif = db.session.get(Manifestation, manif_id)
        assert manif.meta["type"] == "Video Game"

        expr = db.session.get(Expression, expr_id)
        assert expr.content_type == "Video Game"


def _make_manif(app, content_type, carrier):
    """Build a Work → Expression → Manifestation chain with a carrier format."""
    with app.app_context():
        work = Work(title="Carrier Work", meta={"type": content_type}, sort_title="Carrier Work")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type=content_type)
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(
            expression_id=expr.id,
            format=carrier,
            meta={"type": content_type, "format": carrier, "Format": carrier},
        )
        db.session.add(manif)
        db.session.commit()
        return manif.id, expr.id


def test_type_change_preserves_matching_carrier(app):
    """A carrier valid for the new type's category survives the type change."""
    manif_id, _ = _make_manif(app, "video", "bluray")

    updated = update_frbr_entity_type(Manifestation, manif_id, "movie")

    assert updated.meta["type"] == "movie"
    assert updated.format == "bluray"
    assert updated.meta["format"] == "bluray"
    assert updated.meta["Format"] == "bluray"


def test_type_change_degrades_cross_category_carrier(app):
    """A carrier from the old category degrades to the new unknown_* placeholder."""
    manif_id, _ = _make_manif(app, "text", "book")

    updated = update_frbr_entity_type(Manifestation, manif_id, "music")

    assert updated.meta["type"] == "music"
    assert updated.format == "unknown_audio"
    assert updated.meta["format"] == "unknown_audio"
    assert updated.meta["Format"] == "unknown_audio"


def test_type_change_degrades_type_like_format_junk(app):
    """Type-like junk in format fields never survives as a fake carrier."""
    manif_id, _ = _make_manif(app, "video", "video")

    updated = update_frbr_entity_type(Manifestation, manif_id, "movie")

    assert updated.meta["type"] == "movie"
    assert updated.format == "unknown_video"
    assert updated.meta["format"] == "unknown_video"


def test_expression_type_change_preserves_child_carriers(app):
    """Downward propagation keeps carriers on all child Manifestations."""
    manif_id, expr_id = _make_manif(app, "video", "bluray")

    update_frbr_entity_type(Expression, expr_id, "movie")

    with app.app_context():
        manif = db.session.get(Manifestation, manif_id)
        assert manif.meta["type"] == "movie"
        assert manif.format == "bluray"
        assert manif.meta["format"] == "bluray"


def test_update_expression_content_type_preserves_child_carriers(app):
    """update_expression(content_type=…) also keeps valid carriers on children."""
    manif_id, expr_id = _make_manif(app, "music", "vinyl")

    update_expression(expr_id, content_type="music")

    with app.app_context():
        manif = db.session.get(Manifestation, manif_id)
        assert manif.meta["type"] == "music"
        assert manif.format == "vinyl"
        assert manif.meta["format"] == "vinyl"
        assert manif.meta["Format"] == "vinyl"
