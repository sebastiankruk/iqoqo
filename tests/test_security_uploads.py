# tests/test_security_uploads.py
import io
import os
from unittest.mock import patch

import pytest
from werkzeug.datastructures import FileStorage

# Adjust import based on your exact app structure
from app.utils.images import save_upload_image

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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


def test_prevent_directory_traversal_on_image_upload():
    """
    SECURITY TEST: Ensure directory traversal payloads in uploaded filenames
    are sanitized and cannot write outside the intended gallery/covers directory.
    """
    # 1. Arrange: Create a payload designed to escape the upload directory
    malicious_filename = "../../../../etc/cron.d/malicious_reverse_shell"
    file_content = b"fake image data"

    mock_file = FileStorage(stream=io.BytesIO(file_content), filename=malicious_filename, content_type="image/jpeg")

    # Mock the actual file writing and directory paths to avoid polluting the host system during tests
    with patch("app.utils.images.optimize_and_save_image") as mock_optimize_and_save:
        # 2. Act: Attempt to save the malicious upload
        try:
            # We assume covers.py defines GALLERY_DIR as the base directory
            result_url = save_upload_image(mock_file, subfolder="gallery")

            # 3. Assert: Verify the filename was sanitized
            # Werkzeug's secure_filename turns "../../../../etc..." into "etc_cron.d_malicious_reverse_shell"
            assert "../" not in result_url, "Path traversal payload leaked into the return URL!"

            # Verify the actual filepath passed to the save function is safe
            called_path = mock_optimize_and_save.call_args[0][1]
            assert ".." not in called_path, "Application attempted to write to a traversed path!"
            assert called_path.endswith("etc_cron.d_malicious_reverse_shell"), "Filename was not properly sanitized!"

        except ValueError as e:
            # If your implementation explicitly rejects invalid names rather than sanitizing them,
            # this is also a secure outcome.
            assert str(e) == "Invalid filename"
