#!/usr/bin/env python3
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
"""Check status of iQoQo MemPalace wing."""

import shutil
import subprocess
import sys
from pathlib import Path


def find_mempalace() -> str:
    """Find mempalace executable."""
    venv_bin = Path.cwd() / ".venv" / "bin" / "mempalace"
    if venv_bin.exists():
        return str(venv_bin)

    system_bin = shutil.which("mempalace")
    if system_bin:
        return system_bin

    print("Error: mempalace CLI not found in .venv or system PATH.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    """Run mempalace status and report."""
    mempalace_bin = find_mempalace()
    print("=" * 60)
    print("  iQoQo MemPalace Status (Wing: iqoqo)")
    print("=" * 60)

    subprocess.run([mempalace_bin, "status"], text=True)


if __name__ == "__main__":
    main()
