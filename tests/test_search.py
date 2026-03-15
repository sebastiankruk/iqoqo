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


def test_search_items_by_title(client, admin_headers):
    """Ensure full-text search endpoint responds and that `q` filters results."""
    response = client.get("/api/items?q=Hobbit", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    # If any items are returned, they must contain basic keys used by the UI
    if len(data["data"]) > 0:
        first_item = data["data"][0]
        assert "id" in first_item
        assert "title" in first_item

        # Verify that a clearly non-matching query returns no results, ensuring `q` filters.
        no_match_response = client.get("/api/items?q=__no_such_title__", headers=admin_headers)
        assert no_match_response.status_code == 200
        no_match_data = no_match_response.get_json()
        assert no_match_data["success"] is True
        assert isinstance(no_match_data["data"], list)
        assert len(no_match_data["data"]) == 0
