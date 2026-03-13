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
import re
import sys


def extract_release_notes(version: str) -> None:
    try:
        with open("docs/CHANGELOG.md", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("No docs/CHANGELOG.md found.")
        sys.exit(0)

    # Look for the section starting with ## [version] and ending at the next ## [
    pattern = rf"## \[{re.escape(version)}\].*?\n(.*?)(?=\n## \[|$)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if match:
        print(match.group(1).strip())
    else:
        print(f"No release notes found for version {version}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/extract_changelog.py <version>")
        sys.exit(1)

    extract_release_notes(sys.argv[1])
