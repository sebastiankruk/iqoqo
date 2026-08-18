#!/usr/bin/env python3
"""Upsert board game mechanics from ``data/bgg_mechanics.json``.

This script is safe to run repeatedly: existing rows are updated, new rows are
inserted, and rows present in the database but missing from the JSON file are
left untouched (soft preservation).
"""

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

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    data_path = project_root / "data" / "bgg_mechanics.json"

    if not data_path.exists():
        print(f"ERROR: Mechanics data file not found: {data_path}", file=sys.stderr)
        return 1

    with open(data_path, encoding="utf-8") as fh:
        mechanics = json.load(fh)

    if not isinstance(mechanics, list):
        print("ERROR: Expected JSON array of mechanics", file=sys.stderr)
        return 1

    from app import create_app
    from app.db.core import BoardgameMechanic
    from app.db.models import db

    app = create_app()
    with app.app_context():
        now = datetime.now(UTC)
        upserted = 0
        for entry in mechanics:
            slug = entry.get("id")
            if not slug:
                continue

            existing = db.session.execute(select(BoardgameMechanic).where(BoardgameMechanic.id == slug)).scalar_one_or_none()

            if existing is None:
                existing = BoardgameMechanic(id=slug)
                db.session.add(existing)

            existing.name = entry.get("name") or slug
            existing.description = entry.get("description")
            existing.bgg_id = entry.get("bgg_id")
            existing.last_updated = now
            upserted += 1

        db.session.commit()
        print(f"Upserted {upserted} board game mechanics")

    return 0


if __name__ == "__main__":
    sys.exit(main())
