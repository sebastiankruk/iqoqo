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
"""
Script to validate YAML files used by the application.
Specifically tests that `shared/format_mappings.yaml` is structurally valid.
"""

import sys

import yaml


def validate_yaml(file_path: str) -> None:
    """Validate that the given YAML file can be parsed successfully."""
    try:
        with open(file_path, encoding="utf-8") as f:
            yaml.safe_load(f)
        print(f"✅ Successfully validated {file_path}")
    except yaml.YAMLError as e:
        print(f"❌ YAML validation failed for {file_path}:\n{e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"❌ Unexpected error validating {file_path}:\n{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "shared/format_mappings.yaml"
    validate_yaml(file_path)
