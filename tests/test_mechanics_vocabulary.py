"""Tests for the board game mechanics controlled vocabulary."""

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

import json
from pathlib import Path

import pytest

from app.db.core import BoardgameMechanic
from app.db.models import db

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "bgg_mechanics.json"


def test_mechanics_json_file_exists_and_has_entries():
    """The canonical mechanics JSON must exist and contain at least 20 entries."""
    assert DATA_PATH.exists()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 20
    for entry in data:
        assert "id" in entry
        assert "name" in entry
        assert "bgg_id" in entry


def test_mechanics_model_crud(app):
    """BoardgameMechanic rows can be created, read, updated, and deleted."""
    with app.app_context():
        mechanic = BoardgameMechanic(
            id="deck_building",
            name="Deck Building",
            description="Players build a deck during play.",
            bgg_id="2664",
        )
        db.session.add(mechanic)
        db.session.commit()

        stored = db.session.get(BoardgameMechanic, "deck_building")
        assert stored is not None
        assert stored.name == "Deck Building"
        assert stored.bgg_id == "2664"

        stored.name = "Deckbuilding"
        db.session.commit()
        refreshed = db.session.get(BoardgameMechanic, "deck_building")
        assert refreshed.name == "Deckbuilding"

        db.session.delete(refreshed)
        db.session.commit()
        assert db.session.get(BoardgameMechanic, "deck_building") is None


def test_mechanics_seed_from_json(app):
    """Seeding from data/bgg_mechanics.json loads all mechanics into the table."""
    with app.app_context():
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        for entry in data:
            db.session.add(
                BoardgameMechanic(
                    id=entry["id"],
                    name=entry.get("name") or entry["id"],
                    description=entry.get("description"),
                    bgg_id=entry.get("bgg_id"),
                )
            )
        db.session.commit()

        count = db.session.query(BoardgameMechanic).count()
        assert count >= 20

        first = db.session.get(BoardgameMechanic, data[0]["id"])
        assert first is not None
        assert first.name == data[0]["name"]


def test_mechanics_api_returns_vocabulary(client, admin_headers, app):
    """GET /api/boardgame/mechanics returns the controlled vocabulary."""
    with app.app_context():
        db.session.add(BoardgameMechanic(id="worker_placement", name="Worker Placement", bgg_id="2082"))
        db.session.add(BoardgameMechanic(id="card_drafting", name="Card Drafting", bgg_id="2003"))
        db.session.commit()

    resp = client.get("/api/boardgame/mechanics", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    ids = {m["id"] for m in body["data"]}
    assert "worker_placement" in ids
    assert "card_drafting" in ids
    for m in body["data"]:
        assert "id" in m
        assert "name" in m
