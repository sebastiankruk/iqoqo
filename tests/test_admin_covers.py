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
import io

from app.core import frbr_service
from app.db.models import db


def test_admin_upload_cover_success(client, admin_headers):
    """Test successful client-side cropped cover upload"""
    work = frbr_service.create_work(title="Test Work")
    expr = frbr_service.create_expression(work_id=work.id)
    manif = frbr_service.create_manifestation(expression_id=expr.id, meta={})
    db.session.add(manif)
    db.session.commit()

    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    img_io = io.BytesIO()
    img.save(img_io, "JPEG")
    fake_img_blob = img_io.getvalue()
    data = {
        "manifestation_id": str(manif.id),
        "entity_type": "manifestation",
        "entity_id": str(manif.id),
        "file": (io.BytesIO(fake_img_blob), "cropped.jpg"),
    }

    # admin_headers has the token, but we also manually ensure UPLOAD_COVER permission in the DB or mock.
    # We update the admin user's role to include UPLOAD_COVER or we ensure the payload passes the strict PIL checks.
    # For now, we mainly assert that it reaches the endpoint and doesn't crash on standard validations.
    response = client.post("/api/v1/admin/media/upload-cover", data=data, content_type="multipart/form-data", headers=admin_headers)

    assert response.status_code == 200
    assert response.json["success"] is True
    assert "cover_url" in response.json["data"]
