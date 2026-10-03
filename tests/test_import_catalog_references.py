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
"""C18 1.5: a catalog import must not resolve a reference by coincidence.

`import_data()` remaps old ids to new ones as it inserts, but every lookup
falls back to the id from the file when the mapping is missing:

    new_work_id = work_id_map.get(old_work_id, old_work_id)

`Expression.work_id` is a real foreign key to `catalog.works.id`, so when the
payload omits a Work that an Expression references, the raw file id is used
directly. If it happens to match an existing Work, the Expression attaches to
that Work and the import commits -- silently corrupting the catalog rather than
failing. If nothing matches, the FK violation surfaces only at commit.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.core.data_manager import DataManager
from app.db.models import Expression, Manifestation, User, Work, db


@pytest.fixture
def owner_id(app: Any) -> uuid.UUID:
    """A persisted account, so Item ownership resolves.

    @param app: The Flask application fixture.
    @returns: The new user's id.
    """
    with app.app_context():
        user = User(email="import_dangling_owner@iqoqo.local", google_id="import-dangling-owner")
        db.session.add(user)
        db.session.commit()
        return user.id


def _item(owner: uuid.UUID, manifestation_id: int) -> dict[str, Any]:
    """A minimal valid Item payload.

    @param owner: The owning account id.
    @param manifestation_id: The manifestation this Item references.
    @returns: A dict suitable for the `items` key.
    """
    return {
        "id": 1,
        "manifestation_id": manifestation_id,
        "owner_id": str(owner),
        "status": "want_to_read",
        "collection_status": "available",
    }


def test_expression_referencing_a_missing_work_is_rejected(app: Any, owner_id: uuid.UUID) -> None:
    """An Expression whose Work is absent from the payload must fail the import.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must raise.
    """
    payload = {
        "works": [{"id": 1, "title": "The Hobbit"}],
        # work_id 99 is referenced but never defined in `works`.
        "expressions": [{"id": 1, "work_id": 99, "content_type": "text"}],
        "manifestations": [{"id": 1, "expression_id": 1}],
        "items": [_item(owner_id, 1)],
    }

    with app.app_context():
        with pytest.raises(ValueError, match="work"):
            DataManager.import_data(payload)
        assert Work.query.count() == 0, "a rejected import must leave nothing behind"


def test_dangling_reference_does_not_attach_to_an_unrelated_work(app: Any, owner_id: uuid.UUID) -> None:
    """A file id matching an existing Work must not silently adopt it.

    This is the failure that motivated the guard: the old fallback used the raw
    id, so a Work that already existed at that id absorbed the Expression with no
    error at all.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must raise and leave the existing Work alone.
    """
    with app.app_context():
        incumbent = Work(title="An Entirely Unrelated Book")
        db.session.add(incumbent)
        db.session.commit()
        incumbent_id = incumbent.id

        # The payload deliberately claims a *different* id for its own Work, so
        # the incumbent's id is absent from `works` and any reference to it can
        # only be satisfied by borrowing the existing row.
        payload = {
            "works": [{"id": 500, "title": "The Hobbit"}],
            "expressions": [{"id": 1, "work_id": incumbent_id, "content_type": "text"}],
            "manifestations": [{"id": 1, "expression_id": 1}],
            "items": [_item(owner_id, 1)],
        }

        with pytest.raises(ValueError, match="work"):
            DataManager.import_data(payload)

        assert Expression.query.count() == 0
        assert Work.query.filter_by(title="An Entirely Unrelated Book").count() == 1


def test_manifestation_referencing_a_missing_expression_is_rejected(app: Any, owner_id: uuid.UUID) -> None:
    """A Manifestation whose Expression is absent must fail the import.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must raise.
    """
    payload = {
        "works": [{"id": 1, "title": "The Hobbit"}],
        "expressions": [{"id": 1, "work_id": 1, "content_type": "text"}],
        "manifestations": [{"id": 1, "expression_id": 42}],
        "items": [_item(owner_id, 1)],
    }

    with app.app_context():
        with pytest.raises(ValueError, match="expression"):
            DataManager.import_data(payload)
        assert Manifestation.query.count() == 0


def test_item_referencing_a_missing_manifestation_is_rejected(app: Any, owner_id: uuid.UUID) -> None:
    """An Item whose Manifestation is absent must fail the import.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must raise.
    """
    payload = {
        "works": [{"id": 1, "title": "The Hobbit"}],
        "expressions": [{"id": 1, "work_id": 1, "content_type": "text"}],
        "manifestations": [{"id": 1, "expression_id": 1}],
        # manifestation_id 77 was never defined.
        "items": [_item(owner_id, 77)],
    }

    with app.app_context():
        with pytest.raises(ValueError, match="manifestation"):
            DataManager.import_data(payload)


def test_a_complete_payload_still_imports(app: Any, owner_id: uuid.UUID) -> None:
    """The guard must not reject a well-formed payload.

    Guards that reject everything are worse than no guard.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must succeed.
    """
    payload = {
        "works": [{"id": 1, "title": "The Hobbit"}],
        "expressions": [{"id": 1, "work_id": 1, "content_type": "text"}],
        "manifestations": [{"id": 1, "expression_id": 1, "isbn13": "9780261102217"}],
        "items": [_item(owner_id, 1)],
    }

    with app.app_context():
        result = DataManager.import_data(payload)
        assert result == {"works": 1, "expressions": 1, "manifestations": 1, "items": 1}
        assert Work.query.count() == 1


def test_the_reference_is_resolved_not_matched_by_coincidence(app: Any, owner_id: uuid.UUID) -> None:
    """Ids in the payload are remapped; existing rows are never borrowed.

    Two works whose file ids are 1 and 2 must each be referenced by their own
    Expression. New rows get fresh autoincrement ids, so the check is on the
    *linkage* -- which Work each Expression points at -- not on the ids.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must succeed with correct linkage.
    """
    payload = {
        "works": [{"id": 1, "title": "First"}, {"id": 2, "title": "Second"}],
        "expressions": [
            {"id": 10, "work_id": 2, "content_type": "text"},
            {"id": 11, "work_id": 1, "content_type": "text"},
        ],
        "manifestations": [],
        "items": [],
    }

    with app.app_context():
        DataManager.import_data(payload)

        by_title = {w.title: w for w in Work.query.all()}
        linked = {expr.work.title: expr.work_id for expr in Expression.query.all()}

        # work_id 2 -> 'Second', work_id 1 -> 'First'. If ids were not remapped,
        # the Expression for 'Second' would point at 'First' instead.
        assert linked.get("Second") == by_title["Second"].id, "expression for work 2 must link to 'Second'"
        assert linked.get("First") == by_title["First"].id, "expression for work 1 must link to 'First'"


def test_invalid_status_is_rejected_before_it_reaches_the_database(app: Any, owner_id: uuid.UUID) -> None:
    """An unknown Item status must be refused by validation, naming the valid set.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must raise.
    """
    payload = {
        "works": [{"id": 1, "title": "The Hobbit"}],
        "expressions": [{"id": 1, "work_id": 1, "content_type": "text"}],
        "manifestations": [{"id": 1, "expression_id": 1}],
        "items": [{**_item(owner_id, 1), "status": "to_read"}],
    }

    with app.app_context():
        # `to_read` is the plausible-looking typo for `want_to_read`; it is
        # rejected by ck_items_status at commit, which is where the operator
        # never sees which field was wrong.
        with pytest.raises(ValueError, match="want_to_read"):
            DataManager.import_data(payload)


def test_invalid_collection_status_is_rejected(app: Any, owner_id: uuid.UUID) -> None:
    """An unknown collection_status must be refused the same way.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must raise.
    """
    payload = {
        "works": [{"id": 1, "title": "The Hobbit"}],
        "expressions": [{"id": 1, "work_id": 1, "content_type": "text"}],
        "manifestations": [{"id": 1, "expression_id": 1}],
        "items": [{**_item(owner_id, 1), "collection_status": "shelved"}],
    }

    with app.app_context():
        with pytest.raises(ValueError, match="collection_status"):
            DataManager.import_data(payload)


def test_malformed_dates_are_rejected_with_the_offending_value(app: Any, owner_id: uuid.UUID) -> None:
    """An unparseable date must be reported, not raised as a bare ValueError from fromisoformat.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must raise with a useful message.
    """
    payload = {
        "works": [{"id": 1, "title": "The Hobbit"}],
        "expressions": [{"id": 1, "work_id": 1, "content_type": "text"}],
        "manifestations": [{"id": 1, "expression_id": 1, "publication_date": "last spring"}],
        "items": [_item(owner_id, 1)],
    }

    with app.app_context():
        with pytest.raises(ValueError, match="publication_date"):
            DataManager.import_data(payload)


def test_a_work_without_a_title_is_rejected(app: Any, owner_id: uuid.UUID) -> None:
    """A Work with a blank title must be refused before it reaches a NOT NULL column.

    @param app: The Flask application fixture.
    @param owner_id: A valid account for Item ownership.
    @returns: Nothing; the import must raise.
    """
    payload = {
        "works": [{"id": 1, "title": "   "}],
        "expressions": [{"id": 1, "work_id": 1, "content_type": "text"}],
        "manifestations": [{"id": 1, "expression_id": 1}],
        "items": [_item(owner_id, 1)],
    }

    with app.app_context():
        with pytest.raises(ValueError, match="title"):
            DataManager.import_data(payload)
