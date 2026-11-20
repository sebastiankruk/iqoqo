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
"""Tests for C132 collision-free 977 periodical scanning, disambiguation, and ingestion."""

import pytest

from app.core.frbr_service import create_expression, create_manifestation, create_work
from app.core.ingest import IngestService
from app.core.taxonomy import MediaFormat
from app.db.models import Manifestation, Work, db
from app.utils.issn import parse_issn_or_977


def test_bare_977_scan_returns_disambiguation_instead_of_first_issue(client, app, normal_user_headers):
    """Scanning bare 9771507596044 when July 2004 (7(58)) exists must NOT silently reuse 7(58)."""
    headers = normal_user_headers
    with app.app_context():
        work = create_work(
            title="National Geographic Polska",
            issn="1507-5966",
            work_kind="serial",
            meta={"publisher": "G+J RBA"},
        )
        expr = create_expression(work_id=work.id, content_type="text", language="pl")
        m_july = create_manifestation(
            expression_id=expr.id,
            ean="9771507596044",
            ean_addon="07",
            issue_number="7",
            cumulative_issue_number=58,
            publication_year=2004,
            publication_month=7,
            format=MediaFormat.MAGAZINE,
            format_type="magazine",
            meta={"cover_headline": "Skarby pod lodem"},
        )
        db.session.commit()
        work_id = work.id
        july_id = m_july.id

    # Preview of bare 13-digit 977 returns serial_disambiguation with July 2004 listed, not direct match
    preview = client.get("/api/lookup/9771507596044", headers=headers)
    assert preview.status_code == 200
    data = preview.json["data"]
    assert data["status"] == "serial_disambiguation"
    assert data["serial_disambiguation"] is True
    assert data["issn"] == "1507-5966"
    assert data["work"]["id"] == work_id
    assert len(data["existing_issues"]) == 1
    assert data["existing_issues"][0]["manifestation_id"] == july_id
    assert data["existing_issues"][0]["full_barcode"] == "977150759604407"
    assert data["prefill"]["title"] == "National Geographic Polska"

    # Blind POST /api/scan with bare 9771507596044 is rejected with 409 serial_disambiguation
    scan_ambig = client.post("/api/scan", json={"barcode": "9771507596044", "format": "magazine"}, headers=headers)
    assert scan_ambig.status_code == 409
    assert scan_ambig.json["status"] == "serial_disambiguation"

    # Scanning full 15-digit December 2004 (977150759604412) ingests a NEW Manifestation under same Work
    scan_dec = client.post(
        "/api/scan",
        json={
            "barcode": "977150759604412",
            "format": "magazine",
            "meta": {
                "title": "National Geographic Polska",
                "issn": "1507-5966",
                "ean": "9771507596044",
                "ean_addon": "12",
                "full_barcode": "977150759604412",
                "issue_number": "12",
                "cumulative_issue_number": 63,
                "publication_year": 2004,
                "publication_month": 12,
                "format": "magazine",
            },
        },
        headers=headers,
    )
    assert scan_dec.status_code == 201
    dec_mid = scan_dec.json["data"]["manifestation_id"]
    assert dec_mid != july_id

    with app.app_context():
        assert db.session.query(Work).filter_by(issn="1507-5966").count() == 1
        assert db.session.query(Manifestation).filter_by(ean="9771507596044").count() == 2
        assert db.session.query(Manifestation).filter_by(full_barcode="977150759604412").one().id == dec_mid


def test_ingest_all_five_ng_polska_issues_under_one_serial_work(app):
    """Ingest all 5 real National Geographic Polska issues under one F18 Serial Work."""
    samples = [
        ("977150759603711", "11", 50, 2003, 11),
        ("977150759604407", "7", 58, 2004, 7),
        ("977150759604412", "12", 63, 2004, 12),
        ("977150759650101", "1", 64, 2005, 1),
        ("977150759650106", "6", 69, 2005, 6),
    ]
    with app.app_context():
        mids = set()
        for barcode, issue_no, cum_no, year, month in samples:
            parsed = parse_issn_or_977(barcode)
            assert parsed is not None
            manif = IngestService.ingest_serial_from_meta(
                {
                    "title": "National Geographic Polska",
                    "issn": parsed["issn"],
                    "ean": parsed["ean"],
                    "ean_addon": parsed["ean_addon"],
                    "full_barcode": parsed["full_barcode"],
                    "issue_number": issue_no,
                    "cumulative_issue_number": cum_no,
                    "publication_year": year,
                    "publication_month": month,
                    "publisher": "G+J RBA",
                    "language": "pl",
                    "format": "magazine",
                }
            )
            mids.add(manif.id)

        assert len(mids) == 5
        works = db.session.query(Work).filter_by(issn="1507-5966").all()
        assert len(works) == 1
        assert works[0].work_kind == "serial"

        with pytest.raises(ValueError, match="Ambiguous bare 977"):
            IngestService.ingest_serial_issue("9771507596044")


def test_manual_serial_save_with_month_or_headline_succeeds_and_ambiguous_returns_400(client, app, normal_user_headers):
    """POST /items/manual saves bare-977 issues with month/headline and returns 400 (never 500) if totally ambiguous."""
    IngestService.ingest_serial_from_meta(
        {
            "title": "National Geographic Polska",
            "issn": "1507-5966",
            "ean": "9771507596044",
            "ean_addon": "07",
            "full_barcode": "977150759604407",
            "issue_number": "7",
            "publication_year": 2004,
            "format": "magazine",
        }
    )

    # 1. Partial manual fields (month + cover_headline, no issue_number/year) must succeed (200), never 500
    ok_res = client.post(
        "/api/items/manual",
        json={
            "Title": "National Geographic Polska",
            "Authors": ["Unknown"],
            "Format": "magazine",
            "ISBN": "9771507596044",
            "Publisher": "Burda Media Polska Sp.",
            "work_kind": "serial",
            "issn": "1507-5966",
            "publication_month": 12,
            "cover_headline": "Poszukiwanie nowej Ziemi",
        },
        headers=normal_user_headers,
    )
    assert ok_res.status_code == 200

    # 2. Completely ambiguous bare-977 manual payload returns 400 Bad Request, never unhandled 500
    bad_res = client.post(
        "/api/items/manual",
        json={
            "Title": "National Geographic Polska",
            "Authors": ["Unknown"],
            "Format": "magazine",
            "ISBN": "9771507596044",
            "work_kind": "serial",
            "issn": "1507-5966",
        },
        headers=normal_user_headers,
    )
    assert bad_res.status_code == 400
    assert "Ambiguous bare 977" in (bad_res.json.get("error") or "")


def test_manual_serial_save_preserves_edition_fields_and_strips_unknown_and_item_noise(client, normal_user_headers):
    """Manual periodical saves persist publisher/issue fields cleanly, strip 'Unknown', and hide item-only noise."""
    res = client.post(
        "/api/items/manual",
        json={
            "Title": "National Geographic Polska",
            "Authors": ["Unknown"],
            "Format": "magazine",
            "ISBN": "9771507596037",
            "Publisher": "G+J RBA",
            "PublicationDate": "2003-11-01",
            "work_kind": "serial",
            "issn": "1507-5966",
            "issue_number": "11",
            "cumulative_issue_number": 50,
            "volume": "5",
            "publication_year": 2003,
            "publication_month": 11,
            "ean_addon": "11",
            "cover_headline": "100 lat lotnictwa",
            "collection_status": "available",
        },
        headers=normal_user_headers,
    )
    assert res.status_code == 200
    manif_id = res.json["data"]["manifestation_id"]

    m_res = client.get(f"/api/manifestations/{manif_id}", headers=normal_user_headers)
    assert m_res.status_code == 200
    m_data = m_res.json["data"]

    assert m_data["authors"] == []
    assert m_data["publisher"] == "G+J RBA"
    assert m_data["issn"] == "1507-5966"
    assert m_data["issue_number"] == "11"
    assert m_data["cumulative_issue_number"] == 50
    assert m_data["volume"] == "5"
    assert m_data["publication_year"] == 2003
    assert m_data["publication_month"] == 11
    assert m_data["year"] == 2003
    assert m_data["ean_addon"] == "11"
    assert m_data["full_barcode"] == "977150759603711"
    assert m_data["publication_date"] == "2003-11-01"

    extra_keys = {entry["key"].lower() for entry in m_data["display"]["additional_details"]}
    assert "collection_status" not in extra_keys
    assert "publicationdate" not in extra_keys

    # Recent / global list / collection list endpoints also strip Unknown and expose edition fields
    recent_res = client.get("/api/manifestations/recent", headers=normal_user_headers)
    assert recent_res.status_code == 200
    recent_match = next(row for row in recent_res.json["data"] if row["id"] == manif_id)
    assert recent_match["authors"] == []
    assert recent_match["issue_number"] == "11"
    assert recent_match["cumulative_issue_number"] == 50
    assert recent_match["publication_year"] == 2003
    assert recent_match["publication_month"] == 11
    assert recent_match["publisher"] == "G+J RBA"

    catalog_res = client.get("/api/manifestations?limit=10", headers=normal_user_headers)
    assert catalog_res.status_code == 200
    catalog_match = next(row for row in catalog_res.json["data"] if row["id"] == manif_id)
    assert catalog_match["authors"] == []
    assert catalog_match["issue_number"] == "11"
    assert catalog_match["publisher"] == "G+J RBA"

    items_res = client.get("/api/items?limit=10", headers=normal_user_headers)
    assert items_res.status_code == 200
    item_match = next(row for row in items_res.json["data"] if row["manifestation_id"] == manif_id)
    assert item_match["authors"] == []
    assert item_match["format"] == "magazine"
    assert item_match["issue_number"] == "11"
    assert item_match["cumulative_issue_number"] == 50
    assert item_match["publication_year"] == 2003
    assert item_match["publication_month"] == 11
    assert item_match["publisher"] == "G+J RBA"


def test_manual_serial_rejects_invalid_month_and_rolls_back_on_item_failure(client, app, normal_user_headers):
    """Manual serial creation rejects out-of-range publication_month (400) and rolls back Work/Manifestation if Item fails."""
    res_bad = client.post(
        "/api/items/manual",
        json={
            "Title": "Bad Month Magazine",
            "Format": "magazine",
            "issn": "1507-5966",
            "publication_month": 99,
        },
        headers=normal_user_headers,
    )
    assert res_bad.status_code == 400

    # collection_status="lent" without borrower fails after ingest_serial_from_meta(..., commit=False)
    res_fail = client.post(
        "/api/items/manual",
        json={
            "Title": "Rollback Serial Work",
            "Format": "magazine",
            "issn": "0032-3500",
            "issue_number": "42",
            "publication_year": 2025,
            "collection_status": "lent",
        },
        headers=normal_user_headers,
    )
    assert res_fail.status_code == 400

    with app.app_context():
        assert db.session.query(Work).filter_by(title="Rollback Serial Work").first() is None
