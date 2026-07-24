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

"""Tests for scripts/validate_yaml.py."""

import tempfile
from pathlib import Path

import pytest

from scripts.validate_yaml import validate_yaml


def test_validate_yaml_valid_file(tmp_path: Path):
    """validate_yaml() succeeds on valid YAML file."""
    yaml_file = tmp_path / "valid.yaml"
    yaml_file.write_text("key: value\nlist:\n  - item1\n", encoding="utf-8")

    # Should not raise SystemExit
    validate_yaml(str(yaml_file))


def test_validate_yaml_invalid_yaml(tmp_path: Path):
    """validate_yaml() exits with code 1 for malformed YAML."""
    yaml_file = tmp_path / "invalid.yaml"
    yaml_file.write_text("key: value\n\tbad indent\n", encoding="utf-8")

    with pytest.raises(SystemExit) as excinfo:
        validate_yaml(str(yaml_file))
    assert excinfo.value.code == 1


def test_validate_yaml_missing_file():
    """validate_yaml() exits with code 1 for nonexistent file."""
    with pytest.raises(SystemExit) as excinfo:
        validate_yaml("/nonexistent/path/file.yaml")
    assert excinfo.value.code == 1
