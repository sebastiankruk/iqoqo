# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from unittest.mock import patch

import pytest

from scripts.fetch_covers import process_cover_synchronization


@patch("scripts.fetch_covers.os.path.exists", return_value=True)
@patch("scripts.fetch_covers.os.walk")
@patch("scripts.fetch_covers.add_center_watermark")
@patch("scripts.fetch_covers.apply_corner_watermark")
def test_process_cover_synchronization_routing(mock_corner, mock_center, mock_walk, mock_exists) -> None:
    """Verifies correct routing and skipping of already watermarked files."""
    mock_walk.return_value = [
        (
            "/data",
            [],
            [
                "placeholder_1.jpg",
                "llm_gen_1.jpg",
                "text.txt",
                "placeholder_1_wm.jpg",
            ],
        )
    ]

    process_cover_synchronization("/data")

    mock_center.assert_called_once_with(
        "/data/placeholder_1.jpg",
        "resources/images/iqoqo-logo.png",
        "/data/placeholder_1_wm.jpg",
    )
    mock_corner.assert_called_once_with(
        "/data/llm_gen_1.jpg",
        "resources/images/iqoqo-logo.png",
        "/data/llm_gen_1_wm.jpg",
    )
