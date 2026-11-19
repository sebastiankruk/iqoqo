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
"""Tests for scripts/llm_usage_report.py execution audit report."""

from datetime import UTC, datetime, timedelta

from app.db import db
from app.db.settings import LLMTelemetry
from scripts.llm_usage_report import _report


def test_llm_usage_report_empty_returns_1(app, capsys):
    """Report exits 1 cleanly when no telemetry rows exist in the window."""
    with app.app_context():
        db.create_all()
        code = _report(hours=24, operation="metadata_extraction", limit=10)
    assert code == 1
    out = capsys.readouterr().out
    assert "No llm_telemetry rows" in out


def test_llm_usage_report_summarizes_providers(app, capsys):
    """Report aggregates provider counts/status and filters old rows outside window."""
    now = datetime.now(UTC).replace(tzinfo=None)
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [
                LLMTelemetry(
                    provider="gemini",
                    user_id="u1",
                    operation_type="metadata_extraction",
                    status="failed",
                    total_duration_seconds=0.3,
                    error_message="API key not valid",
                    created_at=now - timedelta(minutes=10),
                ),
                LLMTelemetry(
                    provider="tesseract",
                    user_id="u1",
                    operation_type="metadata_extraction",
                    status="success",
                    total_duration_seconds=8.5,
                    created_at=now - timedelta(minutes=9),
                ),
                LLMTelemetry(
                    provider="gemini",
                    user_id="u1",
                    operation_type="cover_generation",
                    status="success",
                    total_duration_seconds=6.0,
                    created_at=now - timedelta(days=10),
                ),
            ]
        )
        db.session.commit()

        code = _report(hours=24, operation="metadata_extraction", limit=10)
    assert code == 0
    out = capsys.readouterr().out
    assert "gemini" in out
    assert "failed" in out
    assert "tesseract" in out
    assert "API key not valid" in out
    assert "cover_generation" not in out
