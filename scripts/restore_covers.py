"""Script to restore cover images and metadata from a backup zip file."""

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

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import zipfile

logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config
from app.db import db
from app.db.models import Manifestation


def _find_manifestation(m_data):
    """Resolve one archive entry to a Manifestation, or None.

    Identifiers are tried strongest-first and only when present, because an
    absent field must never widen the query. `isbn13` is unique in the schema,
    so it can only ever match one row; the others are not, so a match on them
    is only trusted once it has been narrowed to a single candidate.

    Args:
        m_data: One entry from the archive's `manifestations` list.

    Returns:
        The matching Manifestation, or None when the entry identifies none or
        more than one row. Returning None is safe: the file has already been
        copied, and an operator can restore that cover by hand.
    """
    for field in ("id", "isbn13", "upc", "ean"):
        value = m_data.get(field)
        if value is None:
            continue
        candidates = Manifestation.query.filter_by(**{field: value}).all()
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            logger.warning(
                "archive entry matches %d manifestations by %s=%s; leaving its cover alone rather than guessing",
                len(candidates),
                field,
                value,
            )
            return None
    return None


def restore_covers(zip_path, app=None):
    """Restore cover files from a backup archive.

    Used after restoring a database dump whose cover directory was not restored
    alongside it."""
    if app is None:
        app = create_app()
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path, "r") as z:
            real_tmp = os.path.realpath(tmp)
            for member in z.infolist():
                member_path = os.path.realpath(os.path.join(real_tmp, member.filename))
                if member_path != real_tmp and not member_path.startswith(real_tmp + os.sep):
                    raise ValueError(f"Zip slip directory traversal detected: {member.filename}")
            z.extractall(tmp)

        # 1. Copy images
        src_covers = os.path.join(tmp, "covers")
        dst_covers = os.path.join(Config.BASE_DIR, "app", "static", "covers")
        if os.path.exists(src_covers):
            shutil.copytree(src_covers, dst_covers, dirs_exist_ok=True)

        # 2. Update DB matching by ID (or ISBN)
        with open(os.path.join(tmp, "metadata.json"), encoding="utf-8") as f:
            data = json.load(f)

        with app.app_context():
            for m_data in data.get("manifestations", []):
                if not m_data.get("cover_url"):
                    continue

                # Match on the strongest identifier the entry actually carries.
                #
                # The previous code was `filter_by(isbn13=m_data.get("isbn13")).first()`.
                # When the entry has no isbn13 that becomes `filter_by(isbn13=None)`,
                # which matches *every* manifestation without one -- and `.first()`
                # picks an arbitrary row, then overwrites its cover_url. Verified: with
                # three isbn-less manifestations the query returned id 1 purely because
                # it came first, and wrote the wrong cover onto it. Restore is the moment
                # a wrong cover is least likely to be noticed, because the operator has
                # just restored a database and expects the covers to match it.
                manif = _find_manifestation(m_data)
                if manif:
                    manif.cover_url = m_data["cover_url"]
                    new_meta = dict(manif.meta or {})
                    if "cover_source" in (m_data.get("meta") or {}):
                        new_meta["cover_source"] = m_data["meta"]["cover_source"]
                        new_meta["cover_status"] = "ready"
                    manif.meta = new_meta
            db.session.commit()
            print("✅ Restore complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("backup_file")
    restore_covers(parser.parse_args().backup_file)
