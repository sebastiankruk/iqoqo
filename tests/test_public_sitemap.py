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
"""Tests for public sitemap XML generation and caching."""

import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta

from app.api.public import generate_sitemap_xml
from app.db.models import Expression, Manifestation, SharedCollection, User, Work, db


def test_generate_sitemap_xml_structure(app):
    """generate_sitemap_xml generates well-formed XML with the Sitemaps namespace."""
    with app.app_context():
        xml_str = generate_sitemap_xml("https://iqoqo.example.com")
        assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        root = ET.fromstring(xml_str)
        assert root.tag == "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset"


def test_sitemap_endpoint_headers(client):
    """GET /api/public/sitemap.xml returns correct Content-Type and Cache-Control headers."""
    resp = client.get("/api/public/sitemap.xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.content_type
    assert resp.headers.get("Cache-Control") == "public, max-age=3600"


def test_sitemap_includes_public_users_and_excludes_private(app, client):
    """Public users appear in sitemap; private users are excluded."""
    with app.app_context():
        pub_user = User(
            email="pub_sitemap@iqoqo.local",
            public_username="visible_user_123",
            display_name="Visible User",
            visibility="public",
        )
        priv_user = User(
            email="priv_sitemap@iqoqo.local",
            public_username="hidden_user_456",
            display_name="Hidden User",
            visibility="private",
        )
        pub_user.set_password("test-password")
        priv_user.set_password("test-password")
        db.session.add_all([pub_user, priv_user])
        db.session.commit()

    resp = client.get("/api/public/sitemap.xml")
    assert resp.status_code == 200
    assert b"visible_user_123" in resp.data
    assert b"hidden_user_456" not in resp.data


def test_sitemap_includes_active_shares_and_excludes_expired(app, client):
    """Active shared collections appear in sitemap; expired ones are excluded."""
    with app.app_context():
        owner = User(email="shares_test@iqoqo.local", display_name="Owner")
        owner.set_password("test-password")
        db.session.add(owner)
        db.session.flush()

        active_share = SharedCollection(
            user_id=owner.id,
            name="Active Collection",
            share_token="active-token-999",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        expired_share = SharedCollection(
            user_id=owner.id,
            name="Expired Collection",
            share_token="expired-token-000",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        db.session.add_all([active_share, expired_share])
        db.session.commit()

    resp = client.get("/api/public/sitemap.xml")
    assert resp.status_code == 200
    assert b"active-token-999" in resp.data
    assert b"expired-token-000" not in resp.data


def test_sitemap_includes_manifestations(app, client):
    """Catalog manifestations appear in sitemap."""
    with app.app_context():
        work = Work(title="Sitemap Work")
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="book", language="eng")
        db.session.add(expr)
        db.session.flush()

        manifestation = Manifestation(expression_id=expr.id, isbn13="9781234567890")
        db.session.add(manifestation)
        db.session.commit()
        m_id = manifestation.id

    resp = client.get("/api/public/sitemap.xml")
    assert resp.status_code == 200
    assert f"/manifestation/{m_id}".encode() in resp.data
