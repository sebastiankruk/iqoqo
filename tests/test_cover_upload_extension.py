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
"""Cover upload must label files with the format actually written.

`optimize_and_save_image()` re-encodes every upload to JPEG
(`out.save(filepath, "JPEG")`), so the stored filename has to say `.jpg`
regardless of what the client called its file. Deriving the extension from
`file.filename` stored JPEG bytes behind a `.png` name, which nginx's
`X-Content-Type-Options: nosniff` turns into an unrenderable cover.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image


def _png_bytes() -> bytes:
    """A real PNG, so the assertion is about the server's naming, not the input."""
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, "PNG")
    return buf.getvalue()


def _upload(client: Any, headers: dict[str, str], filename: str, payload: bytes, entity_id: int):
    return client.post(
        "/api/v1/admin/media/upload-cover",
        data={
            "file": (io.BytesIO(payload), filename),
            "entity_type": "manifestation",
            "entity_id": str(entity_id),
        },
        content_type="multipart/form-data",
        headers=headers,
    )


@pytest.fixture
def covers_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect the covers directory at both import sites so the test writes nowhere real."""
    target = tmp_path / "covers"
    target.mkdir()
    import app.utils.covers as covers_module

    monkeypatch.setattr(covers_module, "COVERS_DIR", str(target))
    import app.api.system as system_module

    monkeypatch.setattr(system_module, "COVERS_DIR", str(target))
    return target


@pytest.fixture
def manifestation_id() -> int:
    """Create a real Manifestation: the endpoint 404s on an unknown entity."""
    from app.core import frbr_service
    from app.db.models import db

    work = frbr_service.create_work(title="Cover Extension Fixture")
    expr = frbr_service.create_expression(work_id=work.id)
    manif = frbr_service.create_manifestation(expression_id=expr.id, meta={})
    db.session.add(manif)
    db.session.commit()
    return manif.id


@pytest.mark.parametrize("sent_as", ["cover.png", "cover.PNG", "cover.webp", "cover.jpg", "cover"])
def test_upload_always_stores_a_jpeg_named_file(
    client: Any,
    admin_headers: dict[str, str],
    covers_dir: Path,
    manifestation_id: int,
    sent_as: str,
) -> None:
    """Whatever extension the client claims, the stored file must be named .jpg."""
    response = _upload(client, admin_headers, sent_as, _png_bytes(), manifestation_id)
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["success"] is True

    stored = list(covers_dir.glob(f"manifestation_{manifestation_id}_cover.*"))
    assert len(stored) == 1, f"expected exactly one stored cover, found {[p.name for p in stored]}"

    name = stored[0].name
    assert name.endswith(".jpg"), f"{sent_as!r} was stored as {name!r}, which mislabels the JPEG bytes"

    # The name must also match the URL handed back to the caller, or the cover
    # resolves to a 404.
    url = body["data"]["cover_url"]
    assert url.rsplit("/", 1)[-1] == name, f"returned {url!r} but stored {name!r}"


def test_stored_cover_bytes_are_really_jpeg(
    client: Any,
    admin_headers: dict[str, str],
    covers_dir: Path,
    manifestation_id: int,
) -> None:
    """The extension and the magic bytes must agree, or nosniff blocks rendering."""
    _upload(client, admin_headers, "cover.png", _png_bytes(), manifestation_id)

    stored = next(iter(covers_dir.glob(f"manifestation_{manifestation_id}_cover.*")))
    assert stored.read_bytes()[:2] == b"\xff\xd8", "expected a JPEG SOI marker"

    with Image.open(stored) as img:
        assert img.format == "JPEG"
