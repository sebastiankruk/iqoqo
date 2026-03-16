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


def test_search_items_by_title(app, client, normal_user_headers):
    """Ensure full-text search endpoint responds and that `q` filters results."""
    from app.db.models import Expression, Item, Manifestation, User, Work, db

    with app.app_context():
        # The normal_user_headers fixture ensures a user exists in the DB
        user = User.query.first()
        if not user:
            user = User(email="test@iqoqo.local", display_name="Test User")
            db.session.add(user)
            db.session.flush()

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

    # Pass auth headers so the endpoint recognizes the user and returns their items
    response = client.get("/api/items?q=Hobbit", headers=normal_user_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    assert len(data["data"]) > 0, "No items returned; database must be seeded with a matching item."

    # If any items are returned, they must contain basic keys used by the UI
    first_item = data["data"][0]
    assert "id" in first_item
    assert "title" in first_item

    # Verify that a clearly non-matching query returns no results, ensuring `q` filters.
    no_match_response = client.get("/api/items?q=__no_such_title__", headers=normal_user_headers)
    assert no_match_response.status_code == 200
    no_match_data = no_match_response.get_json()
    assert no_match_data["success"] is True
    assert isinstance(no_match_data["data"], list)
    assert len(no_match_data["data"]) == 0
