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
"""Safe FRBR ETL Reconciliation with Complete Relationship Coverage.

This module is a backward-compatibility wrapper around the scripts.etl package.
For direct programmatic use, import from scripts.etl.

Usage:
    python scripts/etl_frbr_safe.py [--dry-run] [--backup-dir DIR] [--verbose]
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.etl import (
    ISBN_CLEAN_PATTERN,
    MergeOperation,
    MergePlan,
    RelationshipInventory,
    ReparentPolicy,
    apply_manifestation_merge_plan,
    apply_work_merge_plan,
    build_manifestation_relationship_inventory,
    build_work_relationship_inventory,
    create_complete_backup,
    generate_manifestation_merge_plan,
    generate_work_merge_plan,
    isbn10_to_isbn13,
    main,
    normalize_isbn,
    normalize_to_isbn13,
    run_safe_etl_pipeline,
    verify_backup_coverage,
)

__all__ = [
    "ISBN_CLEAN_PATTERN",
    "MergeOperation",
    "MergePlan",
    "RelationshipInventory",
    "ReparentPolicy",
    "apply_manifestation_merge_plan",
    "apply_work_merge_plan",
    "build_manifestation_relationship_inventory",
    "build_work_relationship_inventory",
    "create_complete_backup",
    "generate_manifestation_merge_plan",
    "generate_work_merge_plan",
    "isbn10_to_isbn13",
    "main",
    "normalize_isbn",
    "normalize_to_isbn13",
    "run_safe_etl_pipeline",
    "verify_backup_coverage",
]

if __name__ == "__main__":
    main()
