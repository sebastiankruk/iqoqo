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
"""Defer tsvector update triggers for bulk-ingestion performance

Revision ID: 20260709_defer_tsvector
Revises: 20260706_harden_intent_vis
Create Date: 2026-07-09

Phase 4 (0.7.8) – Ingestion Performance & UX Polish
----------------------------------------------------
Synchronous ``BEFORE`` triggers that recompute ``tsvector`` columns fire on
every single row during a bulk-ingestion session, causing severe write latency
and saturating the PostgreSQL transaction pool.

This migration converts those triggers to ``CONSTRAINT … DEFERRABLE INITIALLY
DEFERRED AFTER`` triggers so that the full-text index rebuild is postponed until
the transaction COMMIT.  Combined with the ``SET CONSTRAINTS ALL DEFERRED``
preamble in :meth:`~app.core.ingest.IngestService.batch_ingest_manifestations`,
this ensures that N inserts in one session produce exactly one tsvector
recomputation pass instead of N synchronous passes.

Affected triggers
~~~~~~~~~~~~~~~~~
- ``trg_update_video_game_search_vector`` on ``catalog.works``
  (was: ``BEFORE INSERT OR UPDATE``)

The downgrade restores the original ``BEFORE`` trigger behaviour so rollbacks
are safe.
"""
from alembic import op

revision = "20260709_defer_tsvector"
down_revision = "20260706_harden_intent_vis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop the existing synchronous BEFORE trigger on catalog.works
    op.execute("DROP TRIGGER IF EXISTS trg_update_video_game_search_vector ON catalog.works;")

    # 2. Re-create it as a DEFERRABLE INITIALLY DEFERRED AFTER trigger.
    #    Constraint triggers must be AFTER triggers – that is a PostgreSQL rule.
    op.execute("""
        CREATE CONSTRAINT TRIGGER trg_update_video_game_search_vector_deferred
        AFTER INSERT OR UPDATE ON catalog.works
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION catalog.update_video_game_search_vector();
    """)


def downgrade() -> None:
    # Remove the deferred version
    op.execute(
        "DROP TRIGGER IF EXISTS trg_update_video_game_search_vector_deferred ON catalog.works;"
    )

    # Restore the original synchronous BEFORE trigger
    op.execute("""
        CREATE TRIGGER trg_update_video_game_search_vector
        BEFORE INSERT OR UPDATE ON catalog.works
        FOR EACH ROW EXECUTE FUNCTION catalog.update_video_game_search_vector();
    """)
