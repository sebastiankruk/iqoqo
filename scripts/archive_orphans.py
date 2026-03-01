import os
import shutil
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config
from app.db.models import Manifestation

app = create_app()


def archive_orphaned_covers():
    covers_dir = os.path.join(Config.BASE_DIR, "app", "static", "covers")

    # Allow configuration via env var, default to static/archive/covers
    default_archive = os.path.join(Config.BASE_DIR, "app", "static", "archive", "covers")
    archive_dir = os.environ.get("COVERS_ARCHIVE_DIR", default_archive)
    os.makedirs(archive_dir, exist_ok=True)

    with app.app_context():
        # Get all valid file paths from DB
        valid_paths = {os.path.basename(m.cover_path) for m in Manifestation.query.filter(Manifestation.cover_path.isnot(None)).all()}

        archived_count = 0
        for filename in os.listdir(covers_dir):
            # Ignore hidden files
            if filename.startswith("."):
                continue

            # If physical file is NOT in the database, move it to archive
            if filename not in valid_paths:
                src = os.path.join(covers_dir, filename)
                dst = os.path.join(archive_dir, filename)
                shutil.move(src, dst)
                archived_count += 1

        print(f"✅ Archived {archived_count} orphaned cover images.")


if __name__ == "__main__":
    archive_orphaned_covers()
