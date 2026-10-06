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
"""Tests for cleanup of orphaned cover files on DB commit failure.

These tests verify that:
1. Orphaned cover files are cleaned up when DB commit fails
2. No orphaned image files remain after failed uploads
3. File cleanup happens in exception handlers

Related issue: If db.session.commit() fails after save_upload_image succeeds,
the uploaded image file remains orphaned on disk.
"""

import io
import os

import pytest
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from app.api.admin import _discard_saved_cover
from app.core import frbr_service
from app.db.models import Expression, Manifestation, Work, db
from app.utils.covers import COVERS_DIR


def _remove_if_present(path: str) -> None:
    """Delete a cover file if it exists, ignoring a missing file.

    Covers are written to a real directory shared by the whole suite, so a test
    that leaves debris behind can make the *next* test fail for the wrong reason.
    Each test therefore clears only the file it is about to produce.

    @param path: Absolute path to remove.
    @returns: Nothing.
    """
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _jpeg_bytes(size: int = 100) -> bytes:
    """Build a small valid JPEG.

    @param size: The square image's edge length in pixels.
    @returns: The encoded image bytes.
    """
    buffer = io.BytesIO()
    Image.new("RGB", (size, size), color="red").save(buffer, "JPEG")
    return buffer.getvalue()


def _make_manifestation(app, title: str = "Cover Cleanup Target") -> int:
    """Create a Work -> Expression -> Manifestation chain and return its id.

    @param app: The Flask application.
    @param title: The Work's title.
    @returns: The new Manifestation's primary key.
    """
    with app.app_context():
        work = Work(title=title)
        db.session.add(work)
        db.session.flush()
        expression = Expression(work_id=work.id, content_type="text")
        db.session.add(expression)
        db.session.flush()
        manifestation = Manifestation(expression_id=expression.id, format="book")
        db.session.add(manifestation)
        db.session.commit()
        return manifestation.id


class TestCoverCleanupOnFailure:
    """Tests for cleanup of orphaned cover files on DB failure."""

    def test_no_orphaned_file_when_the_entity_does_not_exist(self, client, admin_headers, app):
        """A 404 must not leave the uploaded image behind on disk.

        The image is written to disk *before* the entity is looked up, and a
        missing entity returns 404 rather than raising, so the surrounding
        `except` handler never runs. This asserted nothing before, for two
        independent reasons:

        - The request passed raw `bytes` rather than a stream, so Werkzeug
          parsed it as an ordinary form field and `request.files` came back
          empty. The endpoint returned 400 at its parameter check and never
          saved anything, so "no orphan" held trivially.
        - It counted files in `app.config["COVER_UPLOAD_DIR"]`, which is not set,
          falling back to the relative path `covers/`. The code writes to
          `app.utils.covers.COVERS_DIR`, i.e. `app/static/covers/`. The test
          created an empty `./covers` itself and then asserted it stayed empty.

        With a real stream and the real directory, the unfixed endpoint left
        `manifestation_999999999_cover.jpg` behind on every 404 -- publicly
        served from /static/covers/, referenced by no row, never collected.

        @param client: The Flask test client.
        @param admin_headers: Auth headers for an admin.
        @param app: The Flask application.
        @returns: Nothing; a leftover file fails the test.
        """
        # The filename is derived from the entity, not the upload, so the file
        # this request would create is known in advance. Asserting on that exact
        # path rather than diffing the directory means an unrelated file left by
        # another test cannot make this pass or fail for the wrong reason.
        orphan = os.path.join(COVERS_DIR, "manifestation_999999999_cover.jpg")
        _remove_if_present(orphan)

        response = client.post(
            "/api/v1/admin/media/upload-cover",
            data={
                "entity_type": "manifestation",
                "entity_id": "999999999",  # Non-existent ID
                "file": (io.BytesIO(_jpeg_bytes()), "orphan-test.jpg"),
            },
            headers=admin_headers,
        )

        assert response.status_code == 404, "a missing entity must report 404, not fall through"
        assert not os.path.exists(orphan), f"orphaned cover file left on disk: {orphan}"

    def test_no_orphaned_file_when_the_commit_fails(self, client, admin_headers, app, monkeypatch):
        """A database failure after the save must delete the file.

        This replaces an `inspect.getsource(upload_cover)` check that searched the
        function's *source text* for any of `os.remove`, `delete`, `cleanup` or
        `finally`. Any one of those words anywhere in the body satisfied it --
        including in a docstring or comment -- so the guard passed whether or not
        cleanup existed, and reported success either way.

        The commit is made to fail for real rather than by patching the removal,
        so the assertion covers the whole path: save, bind, fail, unlink.

        @param client: The Flask test client.
        @param admin_headers: Auth headers for an admin.
        @param app: The Flask application.
        @param monkeypatch: The pytest fixture used to fail the commit.
        @returns: Nothing; a leftover file fails the test.
        """
        entity_id = _make_manifestation(app)
        expected = os.path.join(COVERS_DIR, f"manifestation_{entity_id}_cover.jpg")
        _remove_if_present(expected)

        def explode() -> None:
            raise SQLAlchemyError("simulated commit failure")

        monkeypatch.setattr(db.session, "commit", explode)

        response = client.post(
            "/api/v1/admin/media/upload-cover",
            data={
                "entity_type": "manifestation",
                "entity_id": str(entity_id),
                "file": (io.BytesIO(_jpeg_bytes()), "db-failure.jpg"),
            },
            headers=admin_headers,
        )

        assert response.status_code == 500
        assert not os.path.exists(expected), f"orphaned cover file left on disk: {expected}"

    def test_discard_tolerates_a_file_that_is_already_gone(self):
        """Cleanup must not raise when the file is already absent.

        The handler unlinks a path it recorded optimistically. Between the save
        and the cleanup something else may have removed it -- a concurrent
        upload of the same deterministic filename, or an operator clearing the
        directory -- and the request has already failed, so there is nothing to
        report. Raising here would turn a handled failure into a 500 traceback.

        @returns: Nothing; an exception fails the test.
        """
        _discard_saved_cover(None)
        _discard_saved_cover(os.path.join(COVERS_DIR, "definitely-not-here-9f3a.jpg"))

    def test_a_successful_upload_does_keep_its_file(self, client, admin_headers, app):
        """The positive control: without this, "no orphans" can pass vacuously.

        Every orphan assertion above is also satisfied by an endpoint that never
        writes anything. This pins that a successful upload does create the file,
        binds the URL to the row, and serves the same name the code predicts --
        so the negative tests cannot pass by doing nothing.

        @param client: The Flask test client.
        @param admin_headers: Auth headers for an admin.
        @param app: The Flask application.
        @returns: Nothing; a missing file or unbound URL fails the test.
        """
        entity_id = _make_manifestation(app)
        name = f"manifestation_{entity_id}_cover.jpg"
        stored = os.path.join(COVERS_DIR, name)
        _remove_if_present(stored)

        response = client.post(
            "/api/v1/admin/media/upload-cover",
            data={
                "entity_type": "manifestation",
                "entity_id": str(entity_id),
                "file": (io.BytesIO(_jpeg_bytes()), "success.jpg"),
            },
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert os.path.exists(stored), f"the upload did not create {stored}"
        assert response.get_json()["data"]["cover_url"] == f"/static/covers/{name}"

        with app.app_context():
            entity = db.session.get(Manifestation, entity_id)
            assert entity.meta["cover_url"] == f"/static/covers/{name}"

        os.remove(stored)


class TestFileSystemIntegrity:
    """Tests for file system integrity."""

    def test_covers_directory_is_the_one_the_code_writes_to(self, app):
        """`COVERS_DIR` exists, is writable, and is a real directory.

        This previously read `app.config["COVER_UPLOAD_DIR"]`, which is not set,
        so it fell back to the relative path `covers/` -- created the directory
        as a side effect and then asserted on it. The code writes to
        `app.utils.covers.COVERS_DIR` (`app/static/covers/`), so the test was
        inspecting a stray empty directory it had just made, while the sibling
        test compared file listings inside it. Both were satisfied by an endpoint
        that leaked a file on every failed request.

        The default directory is resolved by `app.utils.covers` at import, so
        simply importing it is what guarantees the two agree.

        @param app: The Flask application.
        @returns: Nothing; a missing or unwritable directory fails the test.
        """
        assert os.path.isdir(COVERS_DIR), f"covers directory does not exist: {COVERS_DIR}"
        assert os.access(COVERS_DIR, os.W_OK), f"covers directory is not writable: {COVERS_DIR}"

    def test_uploaded_covers_are_publicly_served_by_design(self, client, admin_headers, app):
        """Covers live under the static root, so the returned URL must resolve there.

        The previous test here was named `test_covers_are_stored_safely` and its
        docstring claimed covers belong in "a non-public location". Neither was
        true and neither was checked: `STATIC_DIR` is unset in config, so the
        `if static_dir:` guard was always false and the assertion never ran.
        Meanwhile `COVERS_DIR` *is* under `app/static/`, and the endpoint hands
        the client a `/static/covers/...` URL for an `<img>` to load. Public
        readability is the design, not a leak.

        So this pins the design: the URL the API returns names a file that
        actually sits in `COVERS_DIR`. If the storage location and the URL scheme
        ever diverge, the image a user sees breaks -- and this fails rather than
        an assertion that quietly never ran.

        @param client: The Flask test client.
        @param admin_headers: Auth headers for an admin.
        @param app: The Flask application.
        @returns: Nothing; a URL that does not map to the stored file fails.
        """
        entity_id = _make_manifestation(app, title="Public Cover Target")

        response = client.post(
            "/api/v1/admin/media/upload-cover",
            data={
                "entity_type": "manifestation",
                "entity_id": str(entity_id),
                "file": (io.BytesIO(_jpeg_bytes()), "public.jpg"),
            },
            headers=admin_headers,
        )
        assert response.status_code == 200

        cover_url = response.get_json()["data"]["cover_url"]
        assert cover_url.startswith("/static/covers/"), f"unexpected URL shape: {cover_url}"

        served_name = cover_url.removeprefix("/static/covers/")
        stored = os.path.join(COVERS_DIR, served_name)
        assert os.path.exists(stored), f"URL names {served_name!r}, which is not in {COVERS_DIR}"

        os.remove(stored)
