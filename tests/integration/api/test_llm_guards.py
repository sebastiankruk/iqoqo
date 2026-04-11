"""Tests for LLM permission guards and global feature gates."""

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

from io import BytesIO
from unittest.mock import patch

from app.config import Config


def test_extract_from_cover_global_llm_disabled(client, vision_user_headers):
    """Verify that ALLOW_LLM=False blocks extraction even for authorized users."""
    with patch.object(Config, "ALLOW_LLM", False):
        # Mock all fallbacks to return None to simulate "disabled or failed"
        with (
            patch("app.utils.vision._extract_via_gemini") as mock_gemini,
            patch("app.utils.vision._extract_via_ollama") as mock_ollama,
            patch("app.utils.vision._extract_via_tesseract") as mock_tesseract,
            # Mock the extract_metadata_from_cover function to avoid async task execution
            patch("app.api.scanner.extract_metadata_from_cover") as mock_extract,
        ):
            mock_gemini.return_value = None
            mock_ollama.return_value = None
            mock_tesseract.return_value = None
            mock_extract.return_value = None

            data = {"cover": (BytesIO(b"fake-image-data"), "test.jpg")}
            # We need to mock PIL.Image.open and verify as well to pass the initial checks
            with patch("app.api.scanner.Image.open") as mock_image_open:
                mock_image_open.return_value.verify.return_value = None

                response = client.post(
                    "/api/vision/extract",
                    data=data,
                    content_type="multipart/form-data",
                    headers=vision_user_headers,
                )

                assert response.status_code == 202
                task_id = response.json["data"]["task_id"]

                # Now poll for the result, which should be 503 (since all fallbacks return None)
                import time

                max_polls = 10
                for _ in range(max_polls):
                    poll_response = client.get(f"/api/vision/extract/{task_id}", headers=vision_user_headers)
                    if poll_response.status_code != 202:
                        break
                    time.sleep(0.1)

                assert poll_response.status_code == 503
                assert "Vision extraction failed" in poll_response.json["error"]
