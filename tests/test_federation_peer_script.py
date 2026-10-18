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
#
"""Tests for scripts/launch_federation_peer.py helper."""

from __future__ import annotations

import subprocess
import sys

import pytest


def test_launch_federation_peer_seed_only(tmp_path):
    """Verify that --seed-only initializes the sqlite database and exits cleanly."""
    db_file = tmp_path / "peer_test.db"
    db_url = f"sqlite:///{db_file}"

    cmd = [
        sys.executable,
        "scripts/launch_federation_peer.py",
        "--seed-only",
        "--port",
        "5009",
        "--db-url",
        db_url,
        "--peer-username",
        "testpeer",
    ]

    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 0
    assert "Seeded peer database" in res.stdout
    assert "testpeer" in res.stdout
    assert db_file.exists()


def test_wait_for_peer_timeout():
    """Verify wait_for_peer returns False when target port is unreachable."""
    from scripts.launch_federation_peer import wait_for_peer

    # Unbound ephemeral port
    is_ready = wait_for_peer(port=59999, timeout=1)
    assert is_ready is False
