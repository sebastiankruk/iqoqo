"""Tests for Section 6 Data Correction script (scripts/fix_manifestation_1984.py)."""

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

from app.core.frbr_service import create_expression, create_manifestation, create_work
from app.db.models import Manifestation, db
from scripts.fix_manifestation_1984 import fix_manifestation_1984


def test_fix_manifestation_1984_applies_and_idempotent(app):
    with app.app_context():
        work = create_work("Nineteen Eighty-Four")
        expr = create_expression(work.id, content_type="book")
        manif = create_manifestation(expr.id, format="hardcover", meta={"format": "hardcover"})

        # Run script with custom manifestation id
        applied = fix_manifestation_1984(manif.id)
        assert applied is True

        updated_manif = db.session.get(Manifestation, manif.id)
        assert updated_manif.format == "bluray"
        assert updated_manif.expression.content_type == "movie"
        assert updated_manif.meta["format"] == "bluray"

        # Re-running script must be a no-op
        re_applied = fix_manifestation_1984(manif.id)
        assert re_applied is False
