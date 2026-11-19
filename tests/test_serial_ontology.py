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
"""Tests for C131 FRBRoo F18 Serial Work & Periodical Issue ontology, migration, API, and RDF."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from app.api.auth import generate_internal_jwt
from app.core.format_normalizer import FormatNormalizer, normalize_format
from app.core.frbr_service import create_expression, create_manifestation, create_work
from app.core.meta_display import build_display_projection
from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY, MediaFormat
from app.db.models import Item, SharedCollection, User, db

FRBROO = Namespace("http://iflastandards.info/ns/fr/frbr/frbroo/")
SCHEMA = Namespace("https://schema.org/")
IQOQO = Namespace("https://iqoqo.org/ontology#")


def test_alembic_serial_migration_head_is_linear_and_within_32_chars():
    """Verify linear Alembic DAG with a single head <= 32 characters."""
    repo_root = Path(__file__).resolve().parent.parent
    cfg = Config(str(repo_root / "migrations" / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "migrations"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    assert all(len(rev) <= 32 for rev in heads)


def test_serial_taxonomy_and_format_normalizations():
    """Verify journal/periodical/serial aliases resolve to text / magazine cleanly."""
    FormatNormalizer.reset()
    for raw in ("journal", "periodical", "serial", "czasopismo", "magazyn"):
        assert normalize_format(raw) == MediaFormat.MAGAZINE
        assert FORMAT_ALIAS_TO_CATEGORY[raw] == "text" if raw != "czasopismo" and raw != "magazyn" else True


def test_two_national_geographic_issues_share_serial_work_and_emit_rdf(client, app):
    """Two issues sharing one 977 EAN-13 map to one F18 Serial Work and two distinct Manifestations + RDF triples."""
    with app.app_context():
        user = User(email="serial_collector@iqoqo.local", public_username="serialuser", visibility="public")
        db.session.add(user)
        db.session.commit()

        work = create_work(
            title="National Geographic Polska",
            issn="1507-5966",
            work_kind="serial",
            meta={"publisher": "G+J RBA", "indeks": "323357"},
        )
        expr = create_expression(work_id=work.id, content_type="text", language="pl")

        m_july = create_manifestation(
            expression_id=expr.id,
            ean="9771507596044",
            ean_addon="07",
            issue_number="7",
            cumulative_issue_number=58,
            volume="2004",
            publication_year=2004,
            publication_month=7,
            publisher="G+J RBA",
            format=MediaFormat.MAGAZINE,
            format_type="magazine",
            meta={"cover_headline": "Skarby pod lodem", "indeks": "323357"},
        )
        m_dec = create_manifestation(
            expression_id=expr.id,
            ean="9771507596044",
            ean_addon="12",
            issue_number="12",
            cumulative_issue_number=63,
            volume="2004",
            publication_year=2004,
            publication_month=12,
            publisher="G+J RBA",
            format=MediaFormat.MAGAZINE,
            format_type="magazine",
            meta={"cover_headline": "Tajemnice ewolucji"},
        )
        item_july = Item(owner_id=user.id, manifestation_id=m_july.id, status="read", visibility="public", is_hidden=False)
        db.session.add(item_july)
        share = SharedCollection(user_id=user.id, name="Magazines", filters={"visibility_scope": "public_only"})
        db.session.add(share)
        db.session.commit()

        assert m_july.id != m_dec.id
        assert m_july.ean == m_dec.ean == "9771507596044"
        assert m_july.full_barcode == "977150759604407"
        assert m_dec.full_barcode == "977150759604412"

        headers = {"Authorization": f"Bearer {generate_internal_jwt(user)}"}
        work_id = work.id
        july_id = m_july.id
        item_july_id = item_july.id
        share_token = share.share_token

    # Work API exposes F18 Serial fields & issue Manifestation fields
    work_resp = client.get(f"/api/works/{work_id}", headers=headers)
    assert work_resp.status_code == 200
    w_data = work_resp.json["data"]
    assert w_data["issn"] == "1507-5966"
    assert w_data["work_kind"] == "serial"
    assert len(w_data["expressions"][0]["manifestations"]) == 2
    assert {m["full_barcode"] for m in w_data["expressions"][0]["manifestations"]} == {"977150759604407", "977150759604412"}

    # Manifestation API exposes issue fields + parent serial ISSN
    manif_resp = client.get(f"/api/manifestations/{july_id}", headers=headers)
    assert manif_resp.status_code == 200
    m_data = manif_resp.json["data"]
    assert m_data["issn"] == "1507-5966"
    assert m_data["work_kind"] == "serial"
    assert m_data["issue_number"] == "7"
    assert m_data["cumulative_issue_number"] == 58
    assert m_data["publication_year"] == 2004
    assert m_data["publication_month"] == 7
    assert m_data["ean_addon"] == "07"
    assert m_data["full_barcode"] == "977150759604407"

    # Item API exposes issue & serial Work projection
    item_resp = client.get(f"/api/items/{item_july_id}", headers=headers)
    assert item_resp.status_code == 200
    i_data = item_resp.json["data"]
    assert i_data["issue_number"] == "7"
    assert i_data["full_barcode"] == "977150759604407"
    assert i_data["work"]["issn"] == "1507-5966"
    assert i_data["display"]["fields"]["cover_headline"] == "Skarby pod lodem"

    # Display projection check
    proj = build_display_projection({"cover_headline": "Skarby pod lodem", "issue_number": "7"})
    assert proj["sections"]["cover_headline"] == "Skarby pod lodem"
    assert proj["sections"]["issue_number"] == "7"

    # RDF Turtle / JSON-LD serialization checks
    for url in (
        f"/api/public/manifestations/{july_id}",
        f"/api/public/works/{work_id}",
        f"/api/public/share/{share_token}?format=turtle",
    ):
        fmt = "turtle" if "format=turtle" in url else "json-ld"
        rdf_resp = client.get(url)
        assert rdf_resp.status_code == 200
        g = Graph()
        g.parse(data=rdf_resp.data, format=fmt)
        assert (None, RDF.type, FRBROO.F18_Serial_Work) in g
        assert (None, RDF.type, SCHEMA.Periodical) in g
        assert (None, SCHEMA.issn, Literal("1507-5966")) in g
        assert (None, RDF.type, SCHEMA.PublicationIssue) in g
        assert (None, SCHEMA.issueNumber, Literal("7")) in g
        assert (None, SCHEMA.volumeNumber, Literal("2004")) in g
        assert (None, SCHEMA.gtin13, Literal("9771507596044")) in g
        assert (None, IQOQO.eissn, None) not in g  # absent optional field omitted
