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
import uuid

import jwt
import pytest

from app.core.permissions import PermissionName
from app.db.models import Expression, ImageScan, Item, ItemStatusLog, Manifestation, User, Work, db


def test_item_status_logging(client, normal_user_headers, app):
    """Test that updating item status creates a log entry."""
    # Resolve user from token
    token = normal_user_headers["Authorization"].split(" ")[1]
    payload = jwt.decode(token, app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
    user_id = uuid.UUID(payload["sub"])

    with app.app_context():
        # Create dummy Work -> Expression -> Manifestation
        work = Work(title="Test Work")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="1234567890123")
        db.session.add(manif)
        db.session.flush()

        # Create item with proper field split
        item = Item(manifestation_id=manif.id, owner_id=user_id, status="want_to_read", collection_status="available")
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    # Update status via API
    resp = client.put(f"/api/items/{item_id}", json={"status": "reading"}, headers=normal_user_headers)
    assert resp.status_code == 200

    # Verify log entry exists
    with app.app_context():
        logs = ItemStatusLog.query.filter_by(item_id=item_id).all()
        assert len(logs) == 1
        assert logs[0].old_status == "want_to_read"
        assert logs[0].new_status == "reading"
        assert logs[0].user_id == user_id

    # Get logs via API
    resp = client.get(f"/api/items/{item_id}/logs", headers=normal_user_headers)
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert len(data) == 1
    assert data[0]["new_status"] == "reading"


def test_image_scan_provenance(client, admin_headers, app):
    """Test that manifestation images are stored in the new table."""
    with app.app_context():
        # Create dummy manifestation
        work = Work(title="Test Work")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="1234567890123")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    # Create a real 1x1 transparent pixel image
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (1, 1), color="red")
    img_io = BytesIO()
    img.save(img_io, "JPEG")
    img_io.seek(0)

    data = {"image": (img_io, "test.jpg"), "label": "disc"}

    resp = client.post(f"/api/manifestations/{manif_id}/images", data=data, content_type="multipart/form-data", headers=admin_headers)
    assert resp.status_code == 201

    # Verify table entry
    with app.app_context():
        scan = ImageScan.query.filter_by(manifestation_id=manif_id).first()
        assert scan is not None
        assert scan.scan_type == "disc"
        assert "gallery" in scan.file_path

    # Get images via API
    resp = client.get(f"/api/manifestations/{manif_id}/images", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.get_json()["data"]) == 1
    assert resp.get_json()["data"][0]["label"] == "disc"


def test_cover_provenance_headers(client, app):
    """Test that serving a cover provides provenance headers only when requested."""
    with app.app_context():
        # Create dummy manifestation
        work = Work(title="Test Work")
        db.session.add(work)
        db.session.flush()
        expr = Expression(work_id=work.id, content_type="text")
        db.session.add(expr)
        db.session.flush()
        manif = Manifestation(expression_id=expr.id, isbn13="9999999990001", cover_url="test_cover.jpg")
        manif.update_meta(cover_source="google_books")
        db.session.add(manif)
        db.session.commit()
        manif_id = manif.id

    # Mock the file existing in covers directory
    import os

    from app.api.system import COVERS_DIR

    os.makedirs(COVERS_DIR, exist_ok=True)
    with open(os.path.join(COVERS_DIR, "test_cover.jpg"), "w", encoding="utf-8") as f:
        f.write("fake content")

    # CASE 1: No trigger
    resp = client.get("/api/static/covers/test_cover.jpg")
    assert resp.status_code == 200
    assert resp.headers.get("X-Manifestation-ID") is None

    # CASE 2: Via query param
    resp = client.get("/api/static/covers/test_cover.jpg?include=provenance")
    assert resp.status_code == 200
    assert resp.headers.get("X-Manifestation-ID") == str(manif_id)
    assert resp.headers.get("X-Image-Source") == "google_books"

    # CASE 3: Via header
    resp = client.get("/api/static/covers/test_cover.jpg", headers={"X-Include-Provenance": "1"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Manifestation-ID") == str(manif_id)
    assert resp.headers.get("X-Image-Source") == "google_books"
