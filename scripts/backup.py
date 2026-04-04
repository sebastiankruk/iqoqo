"""Script to create a backup of the iQoQo database and cover images."""

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

import json
import os
import shutil
import sys
from datetime import datetime

from app import create_app
from app.config import Config
from app.core.data_manager import DataManager


def create_export(app=None):
    """Creates a full backup archive of data and covers."""
    if app is None:
        app = create_app()
    with app.app_context():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Prioritize app config over env var for backup destination
        export_base_dir = app.config.get("BACKUP_DIR") or os.environ.get("BACKUP_DIR", os.path.join(Config.BASE_DIR, "exports"))
        backup_dir_name = f"iqoqo_backup_{timestamp}"
        export_dir = os.path.join(export_base_dir, backup_dir_name)

        os.makedirs(export_dir, exist_ok=True)
        print(f"Starting backup to {export_dir}...")

        # 1. Export JSON Metadata
        print("Exporting database...")
        data = DataManager.export_all()
        with open(os.path.join(export_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 2. Copy the covers directory
        print("Archiving covers...")
        covers_source = os.path.join(Config.BASE_DIR, "app", "static", "covers")
        covers_dest = os.path.join(export_dir, "covers")
        if os.path.exists(covers_source):
            shutil.copytree(covers_source, covers_dest)

        # 3. Zip the archive
        print("Compressing archive...")
        archive_path = shutil.make_archive(os.path.join(export_base_dir, backup_dir_name), "zip", export_dir)

        # Cleanup unzipped folder
        shutil.rmtree(export_dir)
        print(f"✅ Export complete: {archive_path}")


if __name__ == "__main__":
    # Add project root to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    create_export()
