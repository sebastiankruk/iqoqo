# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#

from datetime import UTC, datetime, timedelta

from app.db.models import Expression, Manifestation, Work, db
from app.utils.covers import cleanup_stuck_pending_covers


def test_cleanup_stuck_pending_covers(app):
    """Test that stuck pending/processing tasks are cleaned up after a timeout."""
    with app.app_context():
        # Clear existing manifestations to have a clean test
        db.session.query(Manifestation).delete()
        db.session.query(Expression).delete()
        db.session.query(Work).delete()
        db.session.commit()

        work = Work(title="Test Book")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()

        now = datetime.now(UTC)

        # 1. Stuck manifestation (pending 40 mins ago)
        manif_stuck = Manifestation(expression_id=expr.id, isbn13="1111111111111")
        db.session.add(manif_stuck)
        db.session.flush()
        # Set cover_status and cover_status_updated_at manually to simulate time passage
        manif_stuck.update_meta(cover_status="pending", cover_status_updated_at=(now - timedelta(minutes=40)).isoformat())

        # 2. Fresh manifestation (pending 10 mins ago)
        manif_fresh = Manifestation(expression_id=expr.id, isbn13="2222222222222")
        db.session.add(manif_fresh)
        db.session.flush()
        manif_fresh.update_meta(cover_status="pending", cover_status_updated_at=(now - timedelta(minutes=10)).isoformat())

        # 3. Processing manifestation (processing 40 mins ago)
        manif_processing_stuck = Manifestation(expression_id=expr.id, isbn13="3333333333333")
        db.session.add(manif_processing_stuck)
        db.session.flush()
        manif_processing_stuck.update_meta(cover_status="processing", cover_status_updated_at=(now - timedelta(minutes=40)).isoformat())

        # 4. Ready manifestation (ready 40 mins ago - should not be touched)
        manif_ready = Manifestation(expression_id=expr.id, isbn13="4444444444444")
        db.session.add(manif_ready)
        db.session.flush()
        manif_ready.update_meta(cover_status="ready", cover_status_updated_at=(now - timedelta(minutes=40)).isoformat())

        db.session.commit()

        # Run the cleanup function
        cleaned = cleanup_stuck_pending_covers(timeout_minutes=30)
        assert cleaned == 2

        # Refresh from database
        db.session.expire_all()
        m_stuck = Manifestation.query.filter_by(isbn13="1111111111111").one()
        m_fresh = Manifestation.query.filter_by(isbn13="2222222222222").one()
        m_proc_stuck = Manifestation.query.filter_by(isbn13="3333333333333").one()
        m_ready = Manifestation.query.filter_by(isbn13="4444444444444").one()

        assert m_stuck.meta.get("cover_status") == "failed"
        assert m_fresh.meta.get("cover_status") == "pending"
        assert m_proc_stuck.meta.get("cover_status") == "failed"
        assert m_ready.meta.get("cover_status") == "ready"
