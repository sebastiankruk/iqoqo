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
"""Tests for the memory-bounded streaming catalog export.

Verifies that the streamed document is valid JSON and semantically identical
to the buffered :meth:`DataManager.export_all`, that it is produced
incrementally, and that an aborted stream releases its database resources.
"""

import json

import pytest

from app.core.data_manager import DataManager
from app.db.models import Expression, Item, Manifestation, User, Work, db


@pytest.fixture
def export_setup(app):
    """Seed a small FRBR catalog with two users' items."""
    with app.app_context():
        owner = User(email="export_owner@example.com", display_name="Owner")
        other = User(email="export_other@example.com", display_name="Other")
        for user in (owner, other):
            user.set_password("Pass123!")
        db.session.add_all([owner, other])
        db.session.flush()

        work = Work(title="Exported Work", meta={"original_language": "en"})
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        for i in range(3):
            manif = Manifestation(
                expression_id=expr.id,
                isbn13=f"97810000000{i:02d}",
                publisher="Tor",
                meta={"format": "paperback", "cover_url": f"/static/covers/{i}.jpg"},
            )
            db.session.add(manif)
            db.session.flush()
            db.session.add(
                Item(
                    manifestation_id=manif.id,
                    owner_id=owner.id if i % 2 == 0 else other.id,
                    status="reading",
                    collection_status="available",
                )
            )

        db.session.commit()
        return {"owner_id": owner.id}


# ── Valid JSON ─────────────────────────────────────────────────────────


def test_stream_produces_valid_json(app, export_setup):
    with app.app_context():
        payload = "".join(DataManager.stream_export_all())
    parsed = json.loads(payload)
    assert set(parsed) == {"version", "exported_at", "works", "expressions", "manifestations", "items"}


def test_streamed_export_matches_buffered_export(app, export_setup):
    """The streamed document must carry exactly the buffered export's data."""
    with app.app_context():
        streamed = json.loads("".join(DataManager.stream_export_all()))
        buffered = DataManager.export_all()

    for key in ("works", "expressions", "manifestations", "items"):
        assert streamed[key] == buffered[key], f"{key} differs between streamed and buffered export"

    # Only the timestamp is generated per-call and therefore expected to differ.
    assert streamed["version"] == buffered["version"] == "1.0"


def test_stream_contains_every_row(app, export_setup):
    with app.app_context():
        parsed = json.loads("".join(DataManager.stream_export_all()))
    assert len(parsed["works"]) == 1
    assert len(parsed["expressions"]) == 1
    assert len(parsed["manifestations"]) == 3
    assert len(parsed["items"]) == 3


def test_item_owner_ids_are_serialized_as_strings(app, export_setup):
    with app.app_context():
        parsed = json.loads("".join(DataManager.stream_export_all()))
    assert all(isinstance(item["owner_id"], str) for item in parsed["items"])


def test_non_ascii_is_preserved(app, export_setup):
    with app.app_context():
        work = Work.query.first()
        work.title = "Zażółć gęślą jaźń — 日本"
        db.session.commit()

        payload = "".join(DataManager.stream_export_all())
        parsed = json.loads(payload)

    assert parsed["works"][0]["title"] == "Zażółć gęślą jaźń — 日本"
    # ensure_ascii=False must keep the characters literal, not escaped.
    assert "日本" in payload


def test_empty_catalog_still_emits_valid_json(app):
    with app.app_context():
        parsed = json.loads("".join(DataManager.stream_export_all()))
    assert parsed["works"] == []
    assert parsed["items"] == []


# ── Incremental (bounded memory) production ────────────────────────────


def test_stream_is_incremental_not_single_blob(app, export_setup):
    """The generator must yield many chunks, not one giant string.

    A single-blob implementation would defeat the O(1) memory goal.
    """
    with app.app_context():
        chunks = list(DataManager.stream_export_all(batch_size=1))
    assert len(chunks) > 5, f"expected incremental chunks, got {len(chunks)}"
    assert all(isinstance(chunk, str) for chunk in chunks)


def test_batch_size_does_not_change_output(app, export_setup):
    """Batch size is a fetch-tuning knob and must not affect the document."""
    with app.app_context():
        small = json.loads("".join(DataManager.stream_export_all(batch_size=1)))
        large = json.loads("".join(DataManager.stream_export_all(batch_size=1000)))
    # `exported_at` is generated per call, so it is expected to differ.
    small.pop("exported_at")
    large.pop("exported_at")
    assert small == large


# ── Disconnect cleanup ─────────────────────────────────────────────────


def test_aborting_the_stream_closes_resources(app, export_setup):
    """Closing the generator early must not leak the connection or cursor."""
    import gc

    with app.app_context():
        stream = DataManager.stream_export_all(batch_size=1)
        next(stream)  # start iteration
        stream.close()
        gc.collect()

        # The engine must still be usable afterwards: a leaked connection or an
        # unterminated transaction would break the next query.
        assert DataManager.export_all()["manifestations"]


def test_generator_exit_runs_cleanup(app, export_setup):
    """A GeneratorExit at the yield point must run the generator's finally.

    ``gen.close()`` injects GeneratorExit at the suspension point, exactly as
    a client disconnect does.  The exception is swallowed by ``close()`` per
    the generator protocol, so the guarantee is verified indirectly: the
    session/connection cleanup must have completed and the engine must remain
    usable.
    """
    with app.app_context():
        stream = DataManager.stream_export_all(batch_size=1)
        next(stream)
        stream.close()

        # Cleanup ran, so the pooled connection is back and usable.
        assert DataManager.export_all()["items"]


def test_abort_mid_array_does_not_corrupt_later_exports(app, export_setup):
    """Aborting between records must not leave partial state behind."""
    with app.app_context():
        for _ in range(3):
            stream = DataManager.stream_export_all(batch_size=1)
            # Abort at a different point each time.
            next(stream)
            next(stream)
            stream.close()

        parsed = json.loads("".join(DataManager.stream_export_all()))
    assert len(parsed["manifestations"]) == 3


def test_pool_is_not_drained_by_repeated_aborts(app, export_setup):
    """Many aborted exports must not exhaust the connection pool."""
    with app.app_context():
        for _ in range(5):
            stream = DataManager.stream_export_all(batch_size=1)
            next(stream)
            stream.close()

        assert DataManager.export_all()["items"]


# ── Endpoint ───────────────────────────────────────────────────────────


def test_admin_export_endpoint_streams_valid_json(client, admin_headers, app, export_setup):
    resp = client.get("/api/admin/export", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.mimetype == "application/json"
    parsed = json.loads(resp.get_data(as_text=True))
    assert len(parsed["manifestations"]) == 3


def test_admin_export_sets_attachment_headers(client, admin_headers, app, export_setup):
    resp = client.get("/api/admin/export", headers=admin_headers)
    assert "attachment" in resp.headers["Content-Disposition"]
    assert resp.headers["Content-Disposition"].endswith('.json"')
    assert resp.headers["Cache-Control"] == "no-store"


def test_admin_export_requires_auth(client, app, export_setup):
    assert client.get("/api/admin/export").status_code in (401, 403)
