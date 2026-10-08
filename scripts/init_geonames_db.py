#!/usr/bin/env python3
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
"""Initialize or synchronize local offline GeoNames cities database.

Downloads the official GeoNames cities15000 dump (~3.3 MB) and compiles an
indexed SQLite database for sub-millisecond, credential-free geographic resolution.
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import os
import sqlite3
import sys
import urllib.request
import zipfile
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_geonames_db")

GEONAMES_DUMP_URL = "https://download.geonames.org/export/dump/cities15000.zip"
FALLBACK_HTTP_URL = "http://download.geonames.org/export/dump/cities15000.zip"


def _get_default_db_path() -> str:
    env_path = os.environ.get("GEONAMES_DB_PATH")
    if env_path:
        return env_path
    if os.path.exists("/usr/src/app/data"):
        return "/usr/src/app/data/geonames_cities.db"
    cwd_data = os.path.join(os.getcwd(), "data")
    if os.path.exists(cwd_data):
        return os.path.join(cwd_data, "geonames_cities.db")
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "geonames_cities.db",
    )


DEFAULT_DB_PATH = _get_default_db_path()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cities (
    geoname_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    asciiname TEXT NOT NULL,
    country_code TEXT NOT NULL,
    lat REAL,
    lng REAL,
    fcode TEXT,
    population INTEGER
);
CREATE TABLE IF NOT EXISTS alt_names (
    name_lower TEXT NOT NULL,
    geoname_id INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cities_name_lower ON cities(LOWER(name));
CREATE INDEX IF NOT EXISTS idx_cities_asciiname_lower ON cities(LOWER(asciiname));
CREATE INDEX IF NOT EXISTS idx_alt_names_lower ON alt_names(name_lower);
"""


def download_dump(url: str = GEONAMES_DUMP_URL) -> bytes:
    """Download cities15000.zip into memory with SSRF protection and retry."""
    # Ensure URL strictly targets official GeoNames download host
    if not (url.startswith("https://download.geonames.org/") or url.startswith("http://download.geonames.org/")):
        raise ValueError(f"Untrusted download URL: {url}")

    logger.info("Downloading GeoNames cities gazetteer from %s ...", url)
    headers = {"User-Agent": "iqoqo-geonames-sync/1.0"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            logger.info("Downloaded %d bytes successfully.", len(content))
            return content
    except Exception as exc:
        if url == GEONAMES_DUMP_URL:
            logger.warning("HTTPS download failed (%s), retrying with HTTP fallback...", exc)
            return download_dump(FALLBACK_HTTP_URL)
        raise RuntimeError(f"Failed to download GeoNames dump from {url}: {exc}") from exc


def build_database(zip_bytes: bytes, db_path: str) -> int:
    """Extract cities15000.txt from zip in-memory and populate SQLite database."""
    target_dir = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(target_dir, exist_ok=True)

    # Use atomic write via temp file to avoid corrupting active readers
    temp_db_path = f"{db_path}.tmp"
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except OSError:
            pass

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Fast bulk insert PRAGMAs
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")
    cursor.executescript(SCHEMA_SQL)

    total_rows = 0
    batch_cities: list[tuple[Any, ...]] = []
    batch_alts: list[tuple[str, int]] = []
    batch_size = 5000

    logger.info("Parsing cities15000.txt from zip archive...")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Prevent zip slip by directly opening the specific entry name
        if "cities15000.txt" not in zf.namelist():
            raise FileNotFoundError("cities15000.txt not found inside archive")

        with zf.open("cities15000.txt") as raw_file:
            reader = csv.reader(io.TextIOWrapper(raw_file, encoding="utf-8"), delimiter="\t")
            for row in reader:
                if len(row) < 15:
                    continue
                try:
                    gid = int(row[0])
                    name = row[1].strip()
                    asciiname = row[2].strip()
                    lat = float(row[4]) if row[4] else None
                    lng = float(row[5]) if row[5] else None
                    fcode = row[7].strip()
                    country_code = row[8].strip()
                    pop = int(row[14]) if row[14] else 0

                    batch_cities.append((gid, name, asciiname, country_code, lat, lng, fcode, pop))
                    total_rows += 1

                    # Track name variations in alt_names for multilingual lookup
                    seen: set[str] = {name.lower(), asciiname.lower()}
                    batch_alts.append((name.lower(), gid))
                    if asciiname.lower() != name.lower():
                        batch_alts.append((asciiname.lower(), gid))

                    if len(row) > 3 and row[3]:
                        for alt in row[3].split(","):
                            alt_clean = alt.strip()
                            if alt_clean and len(alt_clean) >= 2:
                                alt_lower = alt_clean.lower()
                                if alt_lower not in seen:
                                    seen.add(alt_lower)
                                    batch_alts.append((alt_lower, gid))

                    if len(batch_cities) >= batch_size:
                        cursor.executemany(
                            "INSERT OR REPLACE INTO cities VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            batch_cities,
                        )
                        cursor.executemany(
                            "INSERT INTO alt_names VALUES (?, ?)",
                            batch_alts,
                        )
                        batch_cities.clear()
                        batch_alts.clear()
                except (ValueError, IndexError):
                    continue

            if batch_cities:
                cursor.executemany(
                    "INSERT OR REPLACE INTO cities VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    batch_cities,
                )
                cursor.executemany(
                    "INSERT INTO alt_names VALUES (?, ?)",
                    batch_alts,
                )
                batch_cities.clear()
                batch_alts.clear()

    conn.commit()
    cursor.execute("VACUUM;")
    conn.close()

    # Atomically replace target database
    os.replace(temp_db_path, db_path)
    file_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    logger.info("Successfully built %s: %d cities (%.2f MB).", db_path, total_rows, file_size_mb)
    return total_rows


def verify_database(db_path: str) -> int:
    """Verify that database exists and contains expected minimum rows."""
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cities;")
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row else 0
    except Exception as exc:
        logger.warning("Database verification failed for %s: %s", db_path, exc)
        return 0


def main() -> int:
    """CLI entrypoint for initializing GeoNames cities database."""
    parser = argparse.ArgumentParser(description="Initialize local GeoNames cities database.")
    parser.add_argument(
        "--dest",
        default=os.environ.get("GEONAMES_DB_PATH", DEFAULT_DB_PATH),
        help=f"Path to SQLite database file (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force redownload and rebuild even if database already exists",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing database row count without downloading",
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.dest)

    if args.verify_only:
        count = verify_database(db_path)
        if count >= 20000:
            logger.info("GeoNames database verified: %s (%d cities).", db_path, count)
            return 0
        logger.error("GeoNames database invalid or missing: %s (%d cities).", db_path, count)
        return 1

    if not args.force and os.path.exists(db_path):
        existing_count = verify_database(db_path)
        if existing_count >= 20000:
            logger.info(
                "GeoNames database already exists at %s with %d records. Use --force to rebuild.",
                db_path,
                existing_count,
            )
            return 0

    try:
        zip_bytes = download_dump()
        count = build_database(zip_bytes, db_path)
        if count < 20000:
            logger.error("Database populated with fewer records than expected (%d < 20000).", count)
            return 1
        return 0
    except Exception as exc:
        logger.error("Failed to initialize GeoNames database: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
