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
