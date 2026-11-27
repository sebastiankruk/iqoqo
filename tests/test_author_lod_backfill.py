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
"""Tests for scripts/migrate_author_lod_to_contributors.py backfill and idempotency."""

from __future__ import annotations

from sqlalchemy import select

from app.db import db
from app.db.contributions import Contributor, WorkContribution
from app.db.core import EntityAuditLog, SemanticLink, Work
from scripts.migrate_author_lod_to_contributors import migrate_author_lod_links


def test_author_lod_backfill_dry_run_apply_dedup_and_idempotent(app):
    """Verify dry-run reporting, Contributor migration, conflict precedence deduplication, audit logs, and idempotency."""
    with app.app_context():
        work1 = Work(title="Pet Sematary", meta={"authors": ["Stephen King"]})
        work2 = Work(title="Misery", meta={"authors": ["Stephen King"]})
        work_book_only = Work(title="Non-Author Work", meta={"authors": ["Someone"]})
        db.session.add_all([work1, work2, work_book_only])
        db.session.flush()

        existing_contrib = Contributor(name="Stephen King", type="person")
        db.session.add(existing_contrib)
        db.session.flush()

        # Pre-existing suggested contributor link should lose to a verified legacy link
        pre_existing = SemanticLink(
            entity_type="contributor",
            entity_id=existing_contrib.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Stephen_King",
            pref_label="Stephen King",
            confidence=0.70,
            status="suggested",
            verified=False,
        )
        legacy_verified = SemanticLink(
            entity_type="work",
            entity_id=work1.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Stephen_King",
            pref_label="Stephen King",
            confidence=0.88,
            status="accepted",
            attributes={"role": "author", "dbo_type": "dbo:Person"},
            verified=True,
        )
        # Second legacy link on another Work pointing to same author/URI via dbo:Person
        legacy_dup_work2 = SemanticLink(
            entity_type="work",
            entity_id=work2.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Stephen_King",
            pref_label="Stephen King",
            confidence=0.95,
            status="accepted",
            attributes={"dbo_type": "Person"},
            verified=False,
        )
        # Non-author Work LOD link must stay on entity_type="work"
        work_entity_link = SemanticLink(
            entity_type="work",
            entity_id=work_book_only.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Pet_Sematary",
            pref_label="Pet Sematary",
            confidence=0.95,
            status="accepted",
            attributes={"dbo_type": "dbo:Book"},
            verified=False,
        )
        db.session.add_all([pre_existing, legacy_verified, legacy_dup_work2, work_entity_link])
        db.session.commit()

        legacy_verified_id = legacy_verified.id
        work_entity_link_id = work_entity_link.id

        # 1. Dry run detects 2 legacy rows without mutating DB
        dry = migrate_author_lod_links(db.session, dry_run=True)
        assert dry["scanned"] == 2
        assert dry["deduplicated"] == 2
        assert dry["migrated"] == 0
        assert db.session.get(SemanticLink, legacy_verified_id).entity_type == "work"

        # 2. Apply resolves WorkContributions, keeps highest-precedence verified row on Contributor, logs audits
        applied = migrate_author_lod_links(db.session, dry_run=False)
        assert applied["scanned"] == 2
        assert applied["deduplicated"] == 2
        assert applied["migrated"] == 0

        surviving = (
            db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "contributor",
                    SemanticLink.entity_id == existing_contrib.id,
                    SemanticLink.external_uri == "http://dbpedia.org/resource/Stephen_King",
                )
            )
            .scalars()
            .all()
        )
        assert len(surviving) == 1
        assert surviving[0].id == legacy_verified_id
        assert surviving[0].verified is True

        # Non-author Work link untouched
        assert db.session.get(SemanticLink, work_entity_link_id).entity_type == "work"

        # WorkContributions created for both works
        wc_work_ids = {
            wc.work_id
            for wc in db.session.execute(select(WorkContribution).where(WorkContribution.contributor_id == existing_contrib.id))
            .scalars()
            .all()
        }
        assert wc_work_ids == {work1.id, work2.id}

        # Audit logs recorded
        audits = (
            db.session.execute(
                select(EntityAuditLog).where(
                    EntityAuditLog.entity_type == "contributor",
                    EntityAuditLog.entity_id == existing_contrib.id,
                )
            )
            .scalars()
            .all()
        )
        assert len(audits) == 2

        # 3. Second run is strictly idempotent
        second = migrate_author_lod_links(db.session, dry_run=False)
        assert second == {"scanned": 0, "migrated": 0, "deduplicated": 0, "skipped": 0}


def test_author_lod_backfill_creates_contributor_when_absent(app):
    """When no Contributor exists yet, backfill creates Contributor + WorkContribution and moves link cleanly."""
    with app.app_context():
        work = Work(title="Solaris", meta={"authors": ["Stanislaw Lem"]})
        db.session.add(work)
        db.session.flush()

        legacy_link = SemanticLink(
            entity_type="work",
            entity_id=work.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Stanislaw_Lem",
            pref_label="Stanislaw Lem",
            confidence=0.91,
            status="accepted",
            attributes={"role": "author"},
            verified=False,
        )
        db.session.add(legacy_link)
        db.session.commit()

        result = migrate_author_lod_links(db.session, dry_run=False)
        assert result == {"scanned": 1, "migrated": 1, "deduplicated": 0, "skipped": 0}

        contrib = db.session.execute(select(Contributor).where(Contributor.name == "Stanislaw Lem")).scalar_one()
        migrated = db.session.get(SemanticLink, legacy_link.id)
        assert migrated.entity_type == "contributor"
        assert migrated.entity_id == contrib.id

        wc = db.session.execute(
            select(WorkContribution).where(WorkContribution.work_id == work.id, WorkContribution.contributor_id == contrib.id)
        ).scalar_one()
        assert wc.role == "author"


def test_author_lod_backfill_deletes_loser_before_updating_winner_and_drops_yes_flag(app, monkeypatch):
    """Deduplication executes DELETE before re-pointing winner UPDATE; CLI rejects --yes while keeping prod confirmation."""
    import pytest
    from sqlalchemy import event

    from scripts.migrate_author_lod_to_contributors import _confirm_production_execution, main

    # Dead --yes CLI flag was removed
    with pytest.raises(SystemExit) as exc_info:
        main(["--apply", "--yes"])
    assert exc_info.value.code == 2

    # Production DB confirmation guard remains enforced
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/iqoqo_prod")
    monkeypatch.setattr("builtins.input", lambda _prompt: "wrong_db")
    with pytest.raises(RuntimeError, match="Confirmation mismatch"):
        _confirm_production_execution()

    # Verify SQL statement order: DELETE of loser precedes UPDATE of winner when winner is work link
    statements: list[str] = []

    def _capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.split()))

    with app.app_context():
        w = Work(title="Order Guard Work", meta={"authors": ["Isaac Asimov"]})
        c = Contributor(name="Isaac Asimov", type="person")
        db.session.add_all([w, c])
        db.session.flush()

        loser = SemanticLink(
            entity_type="contributor",
            entity_id=c.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Isaac_Asimov",
            pref_label="Isaac Asimov",
            confidence=0.60,
            status="suggested",
            verified=False,
        )
        winner = SemanticLink(
            entity_type="work",
            entity_id=w.id,
            authority="dbpedia",
            external_uri="http://dbpedia.org/resource/Isaac_Asimov",
            pref_label="Isaac Asimov",
            confidence=0.99,
            status="accepted",
            attributes={"role": "author"},
            verified=True,
        )
        db.session.add_all([loser, winner])
        db.session.commit()

        event.listen(db.engine, "before_cursor_execute", _capture_sql)
        try:
            res = migrate_author_lod_links(db.session, dry_run=False)
        finally:
            event.remove(db.engine, "before_cursor_execute", _capture_sql)

        assert res["deduplicated"] == 1
        delete_indices = [i for i, stmt in enumerate(statements) if "DELETE FROM" in stmt and "semantic_links" in stmt]
        update_indices = [i for i, stmt in enumerate(statements) if "UPDATE" in stmt and "semantic_links" in stmt and "entity_type" in stmt]
        assert delete_indices and update_indices
        assert delete_indices[0] < update_indices[0]
