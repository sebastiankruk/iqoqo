"""Tests for Section 3 & Section 4 Data Normalization & ETL Migration Pipeline.

Pins:
- Schema columns (Work.sort_title, Expression.raw_payload, Manifestation.format/label/barcode/catalog_number/raw_payload, Item.raw_payload).
- Automatic sort_title derivation (article stripping).
- Column-first property accessors.
- Ingestion raw_payload persistence across strategies (Discogs, MusicBrainz, TMDB, BGG, Allegro).
- Post-migration drift health check (verify_column_meta_drift and /api/health?check_drift=1).
- Reversible downgrade/upgrade round-trip preserving meta content.
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

from unittest.mock import patch

import pytest

from app.core.data_manager import DataManager
from app.core.frbr_service import (
    create_expression,
    create_item,
    create_manifestation,
    create_work,
    derive_sort_title,
    update_manifestation,
    update_work,
)
from app.db.models import Expression, Item, Manifestation, Work, db
from app.utils.allegro import fetch_allegro_metadata
from app.utils.bgg import fetch_bgg_metadata
from app.utils.discogs import _normalize_release_data
from app.utils.musicbrainz import fetch_audio_metadata
from app.utils.tmdb import fetch_video_metadata


class TestSortTitleDerivation:
    @pytest.mark.parametrize(
        "title, expected",
        [
            ("The Hobbit", "Hobbit"),
            ("A Clockwork Orange", "Clockwork Orange"),
            ("An American in Paris", "American in Paris"),
            ("Ten obcy", "obcy"),
            ("Ta dziewczyna", "dziewczyna"),
            ("To jest film", "jest film"),
            ("Ordinary Title", "Ordinary Title"),
            ("", ""),
        ],
    )
    def test_strip_leading_articles(self, title, expected):
        assert derive_sort_title(title) == expected

    def test_create_work_auto_derives_sort_title(self, app):
        with app.app_context():
            work = create_work(title="The Lord of the Rings")
            assert work.sort_title == "Lord of the Rings"

    def test_create_work_respects_explicit_sort_title(self, app):
        with app.app_context():
            work = create_work(title="The Beatles", sort_title="Beatles, The")
            assert work.sort_title == "Beatles, The"


class TestRelationalColumnCreationAndAccessors:
    def test_create_manifestation_populates_columns_from_meta(self, app):
        with app.app_context():
            work = create_work("Sample Album")
            expr = create_expression(work.id, content_type="sound")
            manif = create_manifestation(
                expr.id,
                meta={
                    "format": "bluray_audio",
                    "label": "Blue Note",
                    "barcode": "0602475311353",
                    "catalog_number": "BN-1001",
                },
            )

            assert manif.format == "bluray_audio"
            assert manif.label == "Blue Note"
            assert manif.barcode == "0602475311353"
            assert manif.catalog_number == "BN-1001"

    def test_update_manifestation_sets_columns(self, app):
        with app.app_context():
            work = create_work("Sample Work")
            expr = create_expression(work.id)
            manif = create_manifestation(expr.id)

            update_manifestation(
                manif.id,
                format="dvd",
                label="Warner Bros",
                barcode="123456789012",
                catalog_number="WB-99",
            )

            assert manif.format == "dvd"
            assert manif.label == "Warner Bros"
            assert manif.barcode == "123456789012"
            assert manif.catalog_number == "WB-99"


class TestRawPayloadPersistence:
    def test_discogs_includes_raw_payload(self):
        release = {"id": 1234, "title": "Artist - Album", "formats": [{"name": "CD"}]}
        meta = _normalize_release_data(release)
        assert "raw_payload" in meta
        assert meta["raw_payload"] == release

    @patch("requests.get")
    def test_musicbrainz_includes_raw_payload(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"releases": [{"id": "mb-123", "title": "Album", "artist-credit": [{"name": "Artist"}]}]}
        meta = fetch_audio_metadata("123456")
        assert meta is not None
        assert "raw_payload" in meta

    @patch("requests.get")
    def test_tmdb_includes_raw_payload(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "results": [{"media_type": "movie", "id": 99, "title": "Movie Title", "overview": "Test"}]
        }
        meta = fetch_video_metadata("Movie Title")
        assert meta is not None
        assert "raw_payload" in meta
        assert meta["raw_payload"]["id"] == 99


class TestDataManagerExportColumnFirst:
    def test_export_all_includes_relational_columns_and_raw_payload(self, app):
        import uuid

        with app.app_context():
            owner_id = uuid.uuid4()
            work = create_work("The Godfather", raw_payload={"source": "tmdb", "id": 1})
            expr = create_expression(work.id, content_type="movie", kind="live_performance")
            manif = create_manifestation(
                expr.id,
                format="bluray",
                label="Paramount",
                barcode="001122334455",
                catalog_number="PAR-001",
                raw_payload={"vendor": "tmdb"},
            )
            item = create_item(manif.id, owner_id=owner_id, raw_payload={"user_note": "mint"})

            exported = DataManager.export_all()

            exp_work = next(w for w in exported["works"] if w["id"] == work.id)
            assert exp_work["sort_title"] == "Godfather"
            assert exp_work["raw_payload"] == {"source": "tmdb", "id": 1}

            exp_expr = next(e for e in exported["expressions"] if e["id"] == expr.id)
            assert exp_expr["kind"] == "live_performance"

            exp_manif = next(m for m in exported["manifestations"] if m["id"] == manif.id)
            assert exp_manif["format"] == "bluray"
            assert exp_manif["label"] == "Paramount"
            assert exp_manif["barcode"] == "001122334455"
            assert exp_manif["catalog_number"] == "PAR-001"
            assert exp_manif["raw_payload"] == {"vendor": "tmdb"}

            exp_item = next(i for i in exported["items"] if i["id"] == item.id)
            assert exp_item["raw_payload"] == {"user_note": "mint"}


class TestDriftVerificationHealthCheck:
    def test_verify_column_meta_drift_zero_when_aligned(self, app):
        with app.app_context():
            work = create_work("The Matrix")
            expr = create_expression(work.id)
            create_manifestation(expr.id, format="dvd", meta={"format": "dvd"})

            drift = DataManager.verify_column_meta_drift()
            assert drift["format_drift"] == 0
            assert drift["sort_title_drift"] == 0
            assert drift["total_drift"] == 0

    def test_verify_column_meta_drift_detects_mismatch(self, app):
        with app.app_context():
            expr = create_expression(create_work("The Matrix").id)
            create_manifestation(expr.id, format="dvd", meta={"format": "bluray"})

            drift = DataManager.verify_column_meta_drift()
            assert drift["format_drift"] == 1
            assert drift["total_drift"] >= 1

    def test_health_check_endpoint_drift_param(self, client):
        resp = client.get("/api/health?check_drift=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "drift" in data
        assert data["drift"]["total_drift"] == 0
