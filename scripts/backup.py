import json
import os
import shutil
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config
from app.core.data_manager import DataManager

app = create_app()


def create_export():
    """Creates a full backup archive of data and covers."""
    with app.app_context():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_base_dir = os.path.join(Config.BASE_DIR, "exports")
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
    create_export()
