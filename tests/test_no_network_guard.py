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
"""Meta-test: prove the unmocked-ISBN-network guard actually fires.

A guard that never triggers proves nothing, so this file asserts the
guard rejects a deliberately unmocked provider call and still permits an
explicitly mocked one.
"""

import logging
from unittest.mock import patch

import pytest

from app.db.models import Manifestation, db


def test_guard_blocks_unmocked_provider_call(client, app, caplog):
    """A GET for an uncatalogued ISBN with no mock must fail loudly.

    The endpoint wraps provider calls in ``except Exception`` and returns
    502, so the guard's AssertionError surfaces as a 502 response with the
    actionable message in the captured log. A test that forgets the mock
    therefore fails with 502 instead of silently depending on the network.
    """
    with app.app_context():
        # Ensure nothing is catalogued for this ISBN.
        Manifestation.query.filter_by(isbn13="9780441478125").delete()
        db.session.commit()

    with caplog.at_level(logging.ERROR):
        response = client.get("/api/isbn/9780441478125")

    assert response.status_code == 502
    assert "Unmocked call to fetch_isbn_metadata" in caplog.text


def test_guard_allows_explicit_mock(client, app):
    """An explicitly mocked provider call is unaffected by the guard."""
    with app.app_context():
        # Ensure nothing is catalogued for this ISBN.
        Manifestation.query.filter_by(isbn13="9780441478125").delete()
        db.session.commit()

    with patch("app.utils.isbn.fetch_isbn_metadata", return_value={"Title": "Mocked", "Authors": ["Someone"]}):
        response = client.get("/api/isbn/9780441478125")

    assert response.status_code == 200
    assert response.get_json()["Title"] == "Mocked"


def test_guard_error_message_is_actionable(monkeypatch):
    """The failure text must tell the author exactly how to fix it."""
    import app.utils.isbn as isbn_mod

    # The autouse guard is already installed for this test, so calling
    # through the module attribute exercises the real installed callable.
    with pytest.raises(AssertionError) as exc:
        isbn_mod.fetch_isbn_metadata("9780441478125")

    message = str(exc.value)
    assert "Unmocked call to fetch_isbn_metadata" in message
    assert "9780441478125" in message
    # Actionable: names the exact patch target the author should use.
    assert "patch('app.utils.isbn.fetch_isbn_metadata'" in message
