def test_search_items_by_title(client):
    """Ensure full-text search endpoint responds and returns expected envelope."""
    response = client.get("/api/items?q=Hobbit")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    # If any items are returned, they must contain basic keys used by the UI
    if len(data["data"]) > 0:
        assert "id" in data["data"][0]
        assert "title" in data["data"][0]
