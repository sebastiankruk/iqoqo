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

import pathlib
import sys
import tomllib


def main():
    pyproject_path = pathlib.Path("pyproject.toml")
    if not pyproject_path.exists():
        sys.exit("Error: pyproject.toml not found.")

    with pyproject_path.open("rb") as fp:
        data = tomllib.load(fp)

    try:
        # Print only the version so it can be captured by Bash
        print(data["project"]["version"])
    except KeyError as exc:
        raise SystemExit(f"Error: Unable to read [project].version from {pyproject_path}") from exc


if __name__ == "__main__":
    main()
