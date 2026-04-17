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

import pytest

from app.db.models import LLMTelemetry, db
from app.utils.llm_covers import record_telemetry


def test_record_telemetry_success(app):
    """Test recording successful telemetry."""
    with app.app_context():
        record_telemetry("openai", "user1", 1.5, status="success")

        entry = LLMTelemetry.query.filter_by(user_id="user1").first()
        assert entry is not None
        assert entry.provider == "openai"
        assert entry.status == "success"
        assert entry.total_duration_seconds == 1.5
        assert entry.images_generated == 1
        assert entry.estimated_cost_usd > 0


def test_record_telemetry_failure(app):
    """Test recording failed telemetry."""
    with app.app_context():
        record_telemetry("gemini", "user2", 0.5, status="failed", error_message="API Error")

        entry = LLMTelemetry.query.filter_by(user_id="user2").first()
        assert entry is not None
        assert entry.status == "failed"
        assert entry.error_message == "API Error"
        assert entry.images_generated == 0
        assert entry.estimated_cost_usd == 0.0


def test_record_telemetry_not_allowed(app):
    """Test recording not_allowed telemetry."""
    with app.app_context():
        record_telemetry("cloud", "user3", 0.0, status="not_allowed", error_message="Lacks permission")

        entry = LLMTelemetry.query.filter_by(user_id="user3").first()
        assert entry is not None
        assert entry.status == "not_allowed"
        assert entry.error_message == "Lacks permission"
        assert entry.images_generated == 0
