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
"""Performance tests for FRBR safe ETL reconciliation at production scale.

Validates that entity reconciliation across 10,000+ manifestations completes
within bounded execution time and memory limits.
"""

import time
import tracemalloc

import pytest
from sqlalchemy import select

from app.db import db
from app.db.core import Expression, Manifestation, Work
from scripts.etl import run_safe_etl_pipeline

# Scale parameter for performance benchmarking
TARGET_MANIFESTATION_COUNT = 10000
DUPLICATE_GROUP_COUNT = 500  # Generates 500 duplicate pairs among 10K rows
MAX_ACCEPTABLE_DURATION_SECONDS = 30.0
MAX_ACCEPTABLE_PEAK_MEMORY_BYTES = 150 * 1024 * 1024  # 150 MB peak memory bound


@pytest.fixture
def large_manifestation_catalog(app):
    """Seed catalog with 10,000+ manifestations including intentional duplicate pairs."""
    with app.app_context():
        work = Work(title="Scale Benchmark Work", meta={"authors": ["ETL Performance Runner"]})
        db.session.add(work)
        db.session.flush()

        expr = Expression(work_id=work.id, content_type="text", language="en")
        db.session.add(expr)
        db.session.flush()

        # Generate 10,000 manifestation records
        # First (TARGET - DUPLICATE_GROUP_COUNT) are unique ISBNs
        # Remaining DUPLICATE_GROUP_COUNT duplicate the first DUPLICATE_GROUP_COUNT ISBNs
        manifestation_dicts = []
        for i in range(TARGET_MANIFESTATION_COUNT - DUPLICATE_GROUP_COUNT):
            manifestation_dicts.append(
                {
                    "expression_id": expr.id,
                    "isbn13": f"978000{i:07d}",
                    "publisher": f"Publisher {i}",
                    "meta": {"benchmark": True},
                }
            )

        for i in range(DUPLICATE_GROUP_COUNT):
            manifestation_dicts.append(
                {
                    "expression_id": expr.id,
                    "isbn13": f"978-000-{i:07d}",
                    "publisher": f"Duplicate Publisher {i}",
                    "meta": {"benchmark": True, "duplicate": True},
                }
            )

        # Bulk insert for rapid fixture provisioning
        db.session.bulk_insert_mappings(Manifestation, manifestation_dicts)
        db.session.commit()

        total_count = db.session.scalar(select(db.func.count(Manifestation.id)))
        assert total_count >= TARGET_MANIFESTATION_COUNT

        yield {
            "work_id": work.id,
            "expression_id": expr.id,
            "total_count": total_count,
            "expected_duplicates": DUPLICATE_GROUP_COUNT,
        }

        # Cleanup test data
        db.session.execute(db.delete(Manifestation).where(Manifestation.expression_id == expr.id))
        db.session.delete(expr)
        db.session.delete(work)
        db.session.commit()


class TestETLPerformance:
    """Validate time bounds and memory usage during large-scale reconciliation."""

    def test_etl_reconciliation_time_bounds_at_scale(self, app, large_manifestation_catalog):
        """Reconciliation of 10,000+ manifestations must complete within acceptable time bounds (<30s)."""
        with app.app_context():
            start_time = time.perf_counter()
            result = run_safe_etl_pipeline(dry_run=True, verbose=False)
            duration = time.perf_counter() - start_time

            # Assert execution completes within bounded time
            assert (
                duration < MAX_ACCEPTABLE_DURATION_SECONDS
            ), f"ETL reconciliation took {duration:.2f}s, exceeding maximum allowed {MAX_ACCEPTABLE_DURATION_SECONDS}s"

            # Assert merge plans were detected for duplicate pairs
            assert len(result["manifestation_merge_plans"]) >= large_manifestation_catalog["expected_duplicates"]

    def test_etl_memory_usage_bounded_at_scale(self, app, large_manifestation_catalog):
        """Reconciliation memory footprint must remain bounded (<150 MB) during 10K+ row processing."""
        with app.app_context():
            tracemalloc.start()
            try:
                result = run_safe_etl_pipeline(dry_run=True, verbose=False)
                _current, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()

            # Verify memory remains strictly bounded
            peak_mb = peak / (1024 * 1024)
            max_mb = MAX_ACCEPTABLE_PEAK_MEMORY_BYTES / (1024 * 1024)
            assert peak < MAX_ACCEPTABLE_PEAK_MEMORY_BYTES, f"Peak memory usage was {peak_mb:.2f} MB, exceeding {max_mb:.2f} MB bound"
            assert len(result["manifestation_merge_plans"]) >= large_manifestation_catalog["expected_duplicates"]
