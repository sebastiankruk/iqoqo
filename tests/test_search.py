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


import pytest


def test_search_schema_prefix_allowlist_rejects_unexpected_values(monkeypatch):
    import app.core.search_service as search_service

    monkeypatch.setattr(search_service, "_CATALOG", "catalog; DROP SCHEMA auth CASCADE; --.")
    with pytest.raises(ValueError, match="Unexpected database schema prefix configuration"):
        search_service.SearchService._pg_manifestation_fts("needle", limit=10, offset=0)


def test_search_schema_prefix_allowlist_accepts_supported_pairs(monkeypatch):
    import app.core.search_service as search_service

    monkeypatch.setattr(search_service, "_CATALOG", "catalog.")
    monkeypatch.setattr(search_service, "_INVENTORY", "inventory.")
    assert search_service._validated_schema_prefixes() == ("catalog.", "inventory.")

    monkeypatch.setattr(search_service, "_CATALOG", "")
    monkeypatch.setattr(search_service, "_INVENTORY", "")
    assert search_service._validated_schema_prefixes() == ("", "")


def test_pg_manifestation_fts_includes_contributor_search(monkeypatch):
    """The PostgreSQL FTS path must also match Work/Expression contributor names."""
    import app.core.search_service as search_service

    monkeypatch.setattr(search_service, "_USE_PG", True)
    monkeypatch.setattr(search_service, "_CATALOG", "catalog.")
    monkeypatch.setattr(search_service, "_INVENTORY", "inventory.")

    captured = {}

    def fake_execute(stmt, params=None):
        captured["sql"] = str(stmt)
        # Return a value that lets count() succeed and rows() return empty
        if "count" in captured["sql"]:
            return type("R", (), {"scalar": lambda self: 0})()
        return type("R", (), {"all": lambda self: []})()

    monkeypatch.setattr(search_service.db.session, "execute", fake_execute)

    search_service.SearchService._pg_manifestation_fts("Garcia", limit=10, offset=0)

    sql = captured.get("sql", "")
    assert "work_contributions" in sql
    assert "expression_contributions" in sql
    assert "contributors" in sql
    assert "immutable_unaccent(c.name)" in sql


def test_pg_item_fts_includes_contributor_search(monkeypatch):
    """The PostgreSQL item FTS path must also match Work/Expression contributor names."""
    import app.core.search_service as search_service
    from app.core.search_service import ItemSearchFilters

    monkeypatch.setattr(search_service, "_USE_PG", True)
    monkeypatch.setattr(search_service, "_CATALOG", "catalog.")
    monkeypatch.setattr(search_service, "_INVENTORY", "inventory.")

    captured = {}

    def fake_execute(stmt, params=None):
        captured["sql"] = str(stmt)
        if "count" in captured["sql"]:
            return type("R", (), {"scalar": lambda self: 0})()
        return type(
            "R",
            (),
            {
                "mappings": lambda self: type("M", (), {"all": lambda self: []})(),
                "all": lambda self: [],
            },
        )()

    monkeypatch.setattr(search_service.db.session, "execute", fake_execute)

    search_service.SearchService._pg_item_fts(
        "Garcia", user_id="00000000-0000-4000-a000-000000000000", limit=10, offset=0, filters=ItemSearchFilters()
    )

    sql = captured.get("sql", "")
    assert "work_contributions" in sql
    assert "expression_contributions" in sql
    assert "contributors" in sql
    assert "immutable_unaccent(c.name)" in sql


def test_search_items_by_title(app, client, normal_user_headers):
    """Ensure full-text search endpoint responds and that `q` filters results."""
    from app.db.models import Expression, Item, Manifestation, User, Work, db

    with app.app_context():
        # The seeded item is owned by the user whose JWT `normal_user_headers`
        # carries, and /api/items is scoped to the authenticated user -- so the
        # two must be the same account. This used to be `User.query.first()`,
        # which returns whichever row happens to sort first and is only the
        # right user because the fixture happens to create exactly one. Its
        # `if not user:` fallback was worse: it would create a *different*
        # account, so the item would belong to someone the request is not
        # authenticated as and the search would return nothing.
        user = User.query.filter_by(email="test_user@iqoqo.local").one_or_none()
        assert user is not None, "the normal_user_headers fixture did not create test_user@iqoqo.local"

        # Seed database with a matching item so the search yields > 0 results
        work = Work(title="The Hobbit", meta={"authors": ["J.R.R. Tolkien"]})
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="text", language="en", meta={})
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(expression_id=expression.id, isbn13="9780007525492", meta={})
        db.session.add(manifestation)
        db.session.flush()

        # Provide the required owner_id
        item = Item(manifestation_id=manifestation.id, owner_id=user.id, status="available", meta={})
        db.session.add(item)
        db.session.commit()
        seeded_item_id = item.id

    # Pass auth headers so the endpoint recognizes the user and returns their items
    response = client.get("/api/items?q=Hobbit", headers=normal_user_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    assert len(data["data"]) > 0, "No items returned; database must be seeded with a matching item."

    # Assert the row the UI is actually given, not just that it has keys. A
    # shape check (`"title" in first_item`) passes for an empty string, a null,
    # or a title inherited from the wrong work -- which is precisely the class of
    # regression this seeding exists to catch.
    first_item = data["data"][0]
    assert first_item["id"] == seeded_item_id
    assert first_item["title"] == "The Hobbit"

    # Verify that a clearly non-matching query returns no results, ensuring `q` filters.
    no_match_response = client.get("/api/items?q=__no_such_title__", headers=normal_user_headers)
    assert no_match_response.status_code == 200
    no_match_data = no_match_response.get_json()
    assert no_match_data["success"] is True
    assert isinstance(no_match_data["data"], list)
    assert len(no_match_data["data"]) == 0


def test_search_items_by_contributor_and_diacritics(app, client, normal_user_headers):
    """Verify search matches author/contributor names and folds diacritics."""
    from app.db.contributions import Contributor, WorkContribution
    from app.db.models import Expression, Item, Manifestation, User, Work, db

    with app.app_context():
        user = User.query.filter_by(email="test_user@iqoqo.local").one_or_none()
        assert user is not None

        # Seed work with author containing diacritics
        work = Work(title="Cien anos de soledad", meta={"authors": ["Gabriel García Márquez"]})
        db.session.add(work)
        db.session.flush()

        contributor = Contributor(name="Gabriel García Márquez", type="person")
        db.session.add(contributor)
        db.session.flush()

        work_contrib = WorkContribution(work_id=work.id, contributor_id=contributor.id, role="author")
        db.session.add(work_contrib)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="es", meta={})
        db.session.add(expr)
        db.session.flush()

        manif = Manifestation(expression_id=expr.id, isbn13="9780307474728", meta={})
        db.session.add(manif)
        db.session.flush()

        item = Item(manifestation_id=manif.id, owner_id=user.id, status="available", meta={})
        db.session.add(item)

        # Seed another work with Polish diacritics
        work2 = Work(title="Miłość w czasach zarazy", meta={"authors": ["Gabriel García Márquez"]})
        db.session.add(work2)
        db.session.flush()

        work_contrib2 = WorkContribution(work_id=work2.id, contributor_id=contributor.id, role="author")
        db.session.add(work_contrib2)
        db.session.flush()

        expr2 = Expression(work_id=work2.id, content_type="text", language="pl", meta={})
        db.session.add(expr2)
        db.session.flush()

        manif2 = Manifestation(expression_id=expr2.id, isbn13="9788377583648", meta={})
        db.session.add(manif2)
        db.session.flush()

        item2 = Item(manifestation_id=manif2.id, owner_id=user.id, status="available", meta={})
        db.session.add(item2)
        db.session.commit()

        item_id1 = item.id
        item_id2 = item2.id

    # 1. Author search with accented characters
    res = client.get("/api/items?q=García+Márquez", headers=normal_user_headers)
    assert res.status_code == 200
    ids = [it["id"] for it in res.get_json()["data"]]
    assert item_id1 in ids
    assert item_id2 in ids

    # 2. Author search with unaccented characters (Garcia Marquez)
    res_unaccent = client.get("/api/items?q=Garcia+Marquez", headers=normal_user_headers)
    assert res_unaccent.status_code == 200
    ids_unaccent = [it["id"] for it in res_unaccent.get_json()["data"]]
    assert item_id1 in ids_unaccent
    assert item_id2 in ids_unaccent

    # 3. Title search with unaccented characters (milosc -> Miłość)
    res_title_unaccent = client.get("/api/items?q=milosc", headers=normal_user_headers)
    assert res_title_unaccent.status_code == 200
    ids_title = [it["id"] for it in res_title_unaccent.get_json()["data"]]
    assert item_id2 in ids_title
