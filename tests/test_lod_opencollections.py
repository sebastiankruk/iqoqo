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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for OpenCollections.org JSON-LD/RDF owl:sameAs export (C116)."""

import json
import secrets

from app.db.models import Expression, Manifestation, Work, db


def test_lod_manifestation_exports_opencollections_same_as(client, app):
    """GET /api/lod/manifestations/<id> emits opencollections_uri in owl:sameAs / schema:sameAs."""
    oc_m_uri = f"https://opencollections.org/records/m-{secrets.token_hex(4)}"
    oc_w_uri = f"https://opencollections.org/records/w-{secrets.token_hex(4)}"

    with app.app_context():
        work = Work(
            title="LOD OpenCollections Work",
            meta={"authors": ["Test Author"], "lod_links": {"opencollections_uri": oc_w_uri}},
        )
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()
        man = Manifestation(
            expression_id=expr.id,
            format_type="hardcover",
            meta={"lod_links": {"opencollections_uri": oc_m_uri}},
        )
        db.session.add(man)
        db.session.commit()
        man_id = man.id

    resp = client.get(
        f"/api/public/manifestations/{man_id}",
        headers={"Accept": "application/ld+json"},
    )
    assert resp.status_code == 200
    payload_text = resp.get_data(as_text=True)
    data = json.loads(payload_text)
    assert data is not None
    assert oc_m_uri in payload_text
    assert oc_w_uri in payload_text
    assert "sameAs" in payload_text
