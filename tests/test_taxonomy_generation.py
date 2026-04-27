"""Tests for taxonomy generation script."""

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

import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
GENERATOR_SCRIPT = ROOT_DIR / "scripts" / "generate_taxonomy.py"


def test_taxonomy_generation_freshness():
    """Verify that committed taxonomy files match what the generator produces.

    If this test fails, it means someone edited shared/taxonomy.yaml but
    forgot to run 'make generate-taxonomy'.
    """
    # 1. Read current contents
    py_file = ROOT_DIR / "app" / "core" / "taxonomy.py"
    ts_file = ROOT_DIR / "frontend" / "types" / "taxonomy.ts"
    ttl_file = ROOT_DIR / "docs" / "ontology" / "taxonomy.ttl"

    old_py = py_file.read_text()
    old_ts = ts_file.read_text()
    old_ttl = ttl_file.read_text()

    # 2. Run generator
    result = subprocess.run([".venv/bin/python", str(GENERATOR_SCRIPT)], capture_output=True, text=True, check=True, cwd=str(ROOT_DIR))
    assert "Taxonomy generated successfully" in result.stdout

    # 3. Compare
    new_py = py_file.read_text()
    new_ts = ts_file.read_text()
    new_ttl = ttl_file.read_text()

    assert old_py == new_py, "app/core/taxonomy.py is stale. Run 'make generate-taxonomy'."
    assert old_ts == new_ts, "frontend/types/taxonomy.ts is stale. Run 'make generate-taxonomy'."
    assert old_ttl == new_ttl, "docs/ontology/taxonomy.ttl is stale. Run 'make generate-taxonomy'."
