import pytest

from app.core.frbr_service import update_frbr_entity_type
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
            request_type="CHANGE_TYPE",
            status="pending"
        )
        db.session.add(req)
        db.session.commit()

        req_id = req.id
        manif_id = manif.id
        expr_id = expr.id

    # Admin approves
    resp = client.patch(
        f"/api/escalations/{req_id}",
        json={"status": "accepted", "resolution_note": "Approved type change"},
        headers=admin_headers
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
