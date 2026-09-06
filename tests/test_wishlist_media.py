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

"""Tests for Wishlist Media Disambiguation (work_type and medium_type serialization)."""

import pytest

from app.api.auth import generate_internal_jwt
from app.db import db
from app.db.models import Expression, Manifestation, Permission, Role, User, UserWorkIntent, Work


@pytest.fixture
def media_test_setup(app):
    """Seed database with user and various media works (Vinyl, Audio, Game)."""
    with app.app_context():
        user_role = Role.query.filter_by(name="user").first()
        if not user_role:
            user_role = Role(name="user")
            db.session.add(user_role)

        read_item_perm = Permission.query.filter_by(name="read:item").first()
        if not read_item_perm:
            read_item_perm = Permission(name="read:item")
            db.session.add(read_item_perm)

        if read_item_perm not in user_role.permissions:
            user_role.permissions.append(read_item_perm)

        user = User(email="media_wishlist@iqoqo.local", display_name="Media Wishlist Tester")
        user.roles.append(user_role)
        db.session.add(user)
        db.session.flush()

        # 1. Vinyl record work
        vinyl_work = Work(
            title="Abbey Road",
            meta={"authors": ["The Beatles"], "work_type": "AudioWork"},
        )
        db.session.add(vinyl_work)
        db.session.flush()

        vinyl_expr = Expression(
            work_id=vinyl_work.id,
            content_type="music",
            meta={"medium_type": "Vinyl"},
        )
        db.session.add(vinyl_expr)
        db.session.flush()

        vinyl_manif = Manifestation(
            expression_id=vinyl_expr.id,
            format="vinyl",
            meta={"format": "vinyl", "medium_type": "Vinyl"},
        )
        db.session.add(vinyl_manif)
        db.session.flush()

        # 2. Audio/Audiobook work
        audio_work = Work(
            title="Dune Audiobook",
            meta={"authors": ["Frank Herbert"], "work_type": "AudioWork"},
        )
        db.session.add(audio_work)
        db.session.flush()

        audio_expr = Expression(
            work_id=audio_work.id,
            content_type="audiobook",
            meta={"medium_type": "Audio"},
        )
        db.session.add(audio_expr)
        db.session.flush()

        audio_manif = Manifestation(
            expression_id=audio_expr.id,
            format="audiobook_cd",
            meta={"format": "audiobook_cd"},
        )
        db.session.add(audio_manif)
        db.session.flush()

        # 3. Board game work
        game_work = Work(
            title="Catan",
            meta={"authors": ["Klaus Teuber"], "work_type": "GameWork"},
        )
        db.session.add(game_work)
        db.session.flush()

        game_expr = Expression(
            work_id=game_work.id,
            content_type="board_game",
            meta={"medium_type": "BoardGame"},
        )
        db.session.add(game_expr)
        db.session.flush()

        game_manif = Manifestation(
            expression_id=game_expr.id,
            format="board_game",
            meta={"format": "board_game"},
        )
        db.session.add(game_manif)
        db.session.flush()

        db.session.commit()
        return {
            "user_id": user.id,
            "vinyl_work_id": vinyl_work.id,
            "audio_work_id": audio_work.id,
            "game_work_id": game_work.id,
        }


def get_headers(app, user_id):
    """Generate auth headers for a user."""
    with app.app_context():
        user = db.session.get(User, user_id)
        token = generate_internal_jwt(user)
        return {"Authorization": f"Bearer {token}"}


def test_wishlist_vinyl_serialization(client, media_test_setup, app):
    """Ensure Vinyl UserWorkIntent returns work_type='AudioWork' and medium_type='Vinyl'."""
    user_id = media_test_setup["user_id"]
    headers = get_headers(app, user_id)

    with app.app_context():
        intent = UserWorkIntent(user_id=user_id, work_id=media_test_setup["vinyl_work_id"], status="want_to_listen")
        db.session.add(intent)
        db.session.commit()
        intent_id = intent.id

    response = client.get("/api/items?statuses=wish_list", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) >= 1

    vinyl_item = next((item for item in data if item["id"] == -intent_id), None)
    assert vinyl_item is not None
    assert vinyl_item["title"] == "Abbey Road"
    assert vinyl_item["work_type"] == "AudioWork"
    assert vinyl_item["medium_type"] in ("Vinyl", "vinyl")
    assert vinyl_item["content_type"] == "music"

    # Also test detail endpoint
    detail_resp = client.get(f"/api/items/{-intent_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json["data"]
    assert detail_data["work_type"] == "AudioWork"
    assert detail_data["medium_type"] in ("Vinyl", "vinyl")


def test_wishlist_audio_serialization(client, media_test_setup, app):
    """Ensure Audio/Audiobook UserWorkIntent returns work_type='AudioWork' and medium_type='Audio'."""
    user_id = media_test_setup["user_id"]
    headers = get_headers(app, user_id)

    with app.app_context():
        intent = UserWorkIntent(user_id=user_id, work_id=media_test_setup["audio_work_id"], status="want_to_listen")
        db.session.add(intent)
        db.session.commit()
        intent_id = intent.id

    response = client.get("/api/items?statuses=wish_list", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]

    audio_item = next((item for item in data if item["id"] == -intent_id), None)
    assert audio_item is not None
    assert audio_item["title"] == "Dune Audiobook"
    assert audio_item["work_type"] == "AudioWork"
    assert audio_item["medium_type"] in ("Audio", "audiobook_cd")
    assert audio_item["content_type"] == "audiobook"


def test_wishlist_game_serialization(client, media_test_setup, app):
    """Ensure Game UserWorkIntent returns work_type='GameWork' and medium_type='BoardGame'."""
    user_id = media_test_setup["user_id"]
    headers = get_headers(app, user_id)

    with app.app_context():
        intent = UserWorkIntent(user_id=user_id, work_id=media_test_setup["game_work_id"], status="want_to_play")
        db.session.add(intent)
        db.session.commit()
        intent_id = intent.id

    response = client.get("/api/items?statuses=wish_list", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]

    game_item = next((item for item in data if item["id"] == -intent_id), None)
    assert game_item is not None
    assert game_item["title"] == "Catan"
    assert game_item["work_type"] == "GameWork"
    assert game_item["medium_type"] in ("BoardGame", "board_game")
    assert game_item["content_type"] == "board_game"


def test_wishlist_work_level_only_inferred_serialization(client, app):
    """Ensure Work-level intent without manifestation correctly infers or returns work_type."""
    with app.app_context():
        user = User(email="work_level@iqoqo.local", display_name="Work Level Tester")
        db.session.add(user)
        db.session.flush()

        work = Work(
            title="Mysterious Audio Track",
            meta={"authors": ["Artist"], "work_type": "AudioWork", "medium_type": "Vinyl"},
        )
        db.session.add(work)
        db.session.flush()

        intent = UserWorkIntent(user_id=user.id, work_id=work.id, status="want_to_listen")
        db.session.add(intent)
        db.session.commit()

        user_id = user.id
        intent_id = intent.id

    headers = get_headers(app, user_id)
    response = client.get("/api/items?statuses=wish_list", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    item = next((i for i in data if i["id"] == -intent_id), None)
    assert item is not None
    assert item["work_type"] == "AudioWork"
    assert item["medium_type"] == "Vinyl"


def test_wishlist_video_serialization(client, app):
    """Ensure Movie/Video UserWorkIntent returns work_type='VideoWork' and medium_type='DVD'."""
    with app.app_context():
        user = User(email="video_wishlist@iqoqo.local", display_name="Video Tester")
        db.session.add(user)
        db.session.flush()

        video_work = Work(
            title="The Matrix",
            meta={"authors": ["The Wachowskis"], "work_type": "VideoWork"},
        )
        db.session.add(video_work)
        db.session.flush()

        video_expr = Expression(
            work_id=video_work.id,
            content_type="movie",
            meta={"medium_type": "DVD"},
        )
        db.session.add(video_expr)
        db.session.flush()

        video_manif = Manifestation(
            expression_id=video_expr.id,
            format="dvd",
            meta={"format": "dvd", "medium_type": "DVD"},
        )
        db.session.add(video_manif)
        db.session.flush()

        intent = UserWorkIntent(user_id=user.id, work_id=video_work.id, status="want_to_watch")
        db.session.add(intent)
        db.session.commit()

        user_id = user.id
        intent_id = intent.id

    headers = get_headers(app, user_id)
    response = client.get("/api/items?statuses=wish_list", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    video_item = next((i for i in data if i["id"] == -intent_id), None)
    assert video_item is not None
    assert video_item["title"] == "The Matrix"
    assert video_item["work_type"] == "VideoWork"
    assert video_item["medium_type"] in ("DVD", "dvd")
    assert video_item["content_type"] == "movie"

    # Verify detail view
    detail_resp = client.get(f"/api/items/{-intent_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json["data"]
    assert detail_data["work_type"] == "VideoWork"
    assert detail_data["medium_type"] in ("DVD", "dvd")


def test_wishlist_empty_metadata_safe_fallback(client, app):
    """Ensure Work-level intent with empty metadata and no expressions safely falls back without crash."""
    with app.app_context():
        user = User(email="empty_meta@iqoqo.local", display_name="Empty Meta Tester")
        db.session.add(user)
        db.session.flush()

        empty_work = Work(
            title="Book Without Meta",
            meta={},
        )
        db.session.add(empty_work)
        db.session.flush()

        intent = UserWorkIntent(user_id=user.id, work_id=empty_work.id, status="want_to_read")
        db.session.add(intent)
        db.session.commit()

        user_id = user.id
        intent_id = intent.id

    headers = get_headers(app, user_id)
    response = client.get("/api/items?statuses=wish_list", headers=headers)
    assert response.status_code == 200
    data = response.json["data"]
    item = next((i for i in data if i["id"] == -intent_id), None)
    assert item is not None
    assert item["title"] == "Book Without Meta"
    assert item["work_type"] is None
    assert item["medium_type"] is None

    detail_resp = client.get(f"/api/items/{-intent_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json["data"]
    assert detail_data["work_type"] is None
    assert detail_data["medium_type"] is None
