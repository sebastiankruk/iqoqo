import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.config import Config
from app.db import db
from app.db.models import Manifestation

app = create_app()


def restore_covers(zip_path):
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path, "r") as z:
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
                if not m_data.get("cover_path"):
                    continue

                manif = Manifestation.query.filter_by(isbn13=m_data.get("isbn13")).first()
                if manif:
                    manif.cover_path = m_data["cover_path"]
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
