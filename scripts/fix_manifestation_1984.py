"""Idempotent data correction script for Manifestation 1984.

Remaps manifestation ID 1984 to category 'movie' and format 'bluray' per
openspec release-0-7-13 Section 6.

Safe to re-run multiple times as a no-op.
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

import logging

from app.db.models import Manifestation, db

logger = logging.getLogger(__name__)


def fix_manifestation_1984(manifestation_id: int = 1984) -> bool:
    """Remap manifestation with given ID to movie/bluray.

    Returns True if changes were applied, False if already correct or not found.
    """
    manif = db.session.get(Manifestation, manifestation_id)
    if manif is None:
        logger.info("Manifestation %s not found; skipping correction.", manifestation_id)
        return False

    changed = False

    if manif.format != "bluray":
        manif.format = "bluray"
        changed = True

    if manif.expression and manif.expression.content_type != "movie":
        manif.expression.content_type = "movie"
        changed = True

    current_meta = dict(manif.meta or {})
    if current_meta.get("format") != "bluray" or current_meta.get("Format") != "bluray":
        current_meta["format"] = "bluray"
        current_meta["Format"] = "bluray"
        manif.meta = current_meta
        changed = True

    if changed:
        db.session.commit()
        logger.info("Manifestation %s remapped to movie/bluray.", manifestation_id)
        return True

    logger.info("Manifestation %s is already movie/bluray (no-op).", manifestation_id)
    return False


if __name__ == "__main__":
    from run import app

    with app.app_context():
        fix_manifestation_1984()
