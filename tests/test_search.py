def test_search_items_by_title(client):
    """Ensure full-text search endpoint responds and that `q` filters results."""
    response = client.get("/api/items?q=Hobbit")
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
        no_match_response = client.get("/api/items?q=__no_such_title__")
        assert no_match_response.status_code == 200
        no_match_data = no_match_response.get_json()
        assert no_match_data["success"] is True
        assert isinstance(no_match_data["data"], list)
        assert len(no_match_data["data"]) == 0
