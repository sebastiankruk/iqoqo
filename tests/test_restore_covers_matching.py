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
"""C18 2.9: restoring covers must not attach an archive entry to an arbitrary row.

`restore_covers()` matched each archive entry with

    Manifestation.query.filter_by(isbn13=m_data.get("isbn13")).first()

An entry without an `isbn13` makes that `filter_by(isbn13=None)`, which matches
*every* manifestation that has no ISBN -- and `.first()` returns one of them by
storage order. The cover is then written onto that row. Demonstrated below with
three isbn-less manifestations: the query returned id 1 only because it was
first, and the wrong record's cover was overwritten.

A restore is the worst moment to write a wrong cover: the operator has just
restored the database and expects the covers to match it.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.db.models import Expression, Manifestation, Work, db


@pytest.fixture
def three_isbn_less_manifestations(app: Any) -> list[int]:
    """Three manifestations with no ISBN, UPC or EAN.

    @param app: The Flask application fixture.
    @returns: Their ids, in insertion order.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        ids: list[int] = []
        for i in range(3):
            work = Work(title=f"Work {i}")
            db.session.add(work)
            db.session.flush()
            expression = Expression(work_id=work.id, content_type="book")
            db.session.add(expression)
            db.session.flush()
            manifestation = Manifestation(expression_id=expression.id)
            db.session.add(manifestation)
            db.session.flush()
            ids.append(manifestation.id)
        db.session.commit()
        return ids


def _archive(tmp_path: Path, entries: list[dict[str, Any]]) -> str:
    """Write a cover archive containing the given metadata entries.

    @param tmp_path: Directory for the archive.
    @param entries: The `manifestations` entries to write.
    @returns: The archive path.
    """
    path = tmp_path / "covers.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("metadata.json", json.dumps({"manifestations": entries}))
        archive.writestr("covers/one.jpg", b"image")
    return str(path)


def test_an_entry_without_an_identifier_touches_no_row(app: Any, tmp_path: Path, three_isbn_less_manifestations: list[int]) -> None:
    """An unidentifiable entry must not write a cover onto any manifestation.

    @param app: The Flask application fixture.
    @param tmp_path: pytest temporary directory.
    @param three_isbn_less_manifestations: Ids of the isbn-less rows.
    @returns: Nothing; any write fails the test.
    """
    from scripts.restore_covers import restore_covers

    archive = _archive(tmp_path, [{"cover_url": "/static/covers/one.jpg"}])

    with app.app_context(), patch("app.config.Config.BASE_DIR", str(tmp_path)):
        restore_covers(archive, app=app)

        written = [m.id for m in Manifestation.query.filter(Manifestation.cover_url.is_not(None)).all()]
        assert not written, f"covers were written onto unidentified manifestations {written}"


def test_an_entry_matching_by_isbn_still_works(app: Any, tmp_path: Path, three_isbn_less_manifestations: list[int]) -> None:
    """The normal, identified path must keep working.

    @param app: The Flask application fixture.
    @param tmp_path: pytest temporary directory.
    @param three_isbn_less_manifestations: Ids of the isbn-less rows.
    @returns: Nothing; the identified write must succeed.
    """
    from scripts.restore_covers import restore_covers

    target = three_isbn_less_manifestations[1]
    with app.app_context():
        Manifestation.query.filter_by(id=target).one().isbn13 = "9780261102217"
        db.session.commit()

    archive = _archive(
        tmp_path,
        [{"isbn13": "9780261102217", "cover_url": "/static/covers/one.jpg"}],
    )

    with app.app_context(), patch("app.config.Config.BASE_DIR", str(tmp_path)):
        restore_covers(archive, app=app)

        assert Manifestation.query.filter_by(id=target).one().cover_url == "/static/covers/one.jpg"
        others = [m.id for m in Manifestation.query.filter(Manifestation.cover_url.is_not(None)).all() if m.id != target]
        assert not others, f"other manifestations were written to: {others}"


def test_a_unique_non_isbn_identifier_is_used(app: Any, tmp_path: Path, three_isbn_less_manifestations: list[int]) -> None:
    """A UPC that narrows to exactly one row is a legitimate match.

    The fix is not "require isbn13" -- it is "never widen the query with an
    absent field". An entry carrying only a UPC that identifies one row should
    still restore, because refusing it would lose covers that could be matched
    safely.

    @param app: The Flask application fixture.
    @param tmp_path: pytest temporary directory.
    @param three_isbn_less_manifestations: Ids of the isbn-less rows.
    @returns: Nothing; the write must land on the identified row only.
    """
    from scripts.restore_covers import restore_covers

    target = three_isbn_less_manifestations[2]
    with app.app_context():
        Manifestation.query.filter_by(id=target).one().upc = "012345678905"
        db.session.commit()

    archive = _archive(tmp_path, [{"upc": "012345678905", "cover_url": "/static/covers/one.jpg"}])

    with app.app_context(), patch("app.config.Config.BASE_DIR", str(tmp_path)):
        restore_covers(archive, app=app)

        assert Manifestation.query.filter_by(id=target).one().cover_url == "/static/covers/one.jpg"
        others = [m.id for m in Manifestation.query.filter(Manifestation.cover_url.is_not(None)).all() if m.id != target]
        assert not others, f"other manifestations were written to: {others}"


def test_a_shared_identifier_matching_two_rows_is_refused(app: Any, tmp_path: Path, three_isbn_less_manifestations: list[int]) -> None:
    """When two rows share the identifier, neither is written to.

    `upc` and `ean` are indexed but not unique, so a shared value is possible.

    @param app: The Flask application fixture.
    @param tmp_path: pytest temporary directory.
    @param three_isbn_less_manifestations: Ids of the isbn-less rows.
    @returns: Nothing; an ambiguous write fails the test.
    """
    from scripts.restore_covers import restore_covers

    with app.app_context():
        for manifest_id in three_isbn_less_manifestations[:2]:
            Manifestation.query.filter_by(id=manifest_id).one().upc = "012345678905"
        db.session.commit()

    archive = _archive(tmp_path, [{"upc": "012345678905", "cover_url": "/static/covers/one.jpg"}])

    with app.app_context(), patch("app.config.Config.BASE_DIR", str(tmp_path)):
        restore_covers(archive, app=app)

        written = Manifestation.query.filter(Manifestation.cover_url.is_not(None)).count()
        assert written == 0, "an ambiguous identifier must not be resolved by guessing"


def test_the_resolver_returns_none_for_an_empty_entry() -> None:
    """`_find_manifestation` must be a pure lookup with no query on an empty entry.

    @returns: Nothing; a query or a wrong result fails the test.
    """
    from scripts.restore_covers import _find_manifestation

    assert _find_manifestation({}) is None
    assert _find_manifestation({"cover_url": "/x.jpg"}) is None
