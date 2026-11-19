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
"""Serial / periodical lookup strategy backed by ISSN and 977 barcodes."""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.core.taxonomy import MediaCategory, MediaFormat
from app.strategies.base import LookupStrategy
from app.utils.allegro import fetch_allegro_metadata
from app.utils.http_client import SSRFError, safe_get
from app.utils.issn import normalize_issn, parse_issn_or_977

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 5.0


def _clean_marc_title(raw_title: str) -> str:
    """Strip trailing punctuation commonly present in MARC 245$a fields."""
    return raw_title.strip().rstrip(" /:;.,")


def _extract_marc_subfields(bib: dict[str, Any], tag: str) -> list[dict[str, str]]:
    """Collect flattened subfield maps for every MARC field matching *tag*."""
    marc = bib.get("marc")
    if not isinstance(marc, dict):
        return []
    fields = marc.get("fields")
    if not isinstance(fields, list):
        return []
    results: list[dict[str, str]] = []
    for entry in fields:
        if not isinstance(entry, dict) or tag not in entry:
            continue
        tag_val = entry[tag]
        if not isinstance(tag_val, dict):
            continue
        subfields = tag_val.get("subfields")
        if not isinstance(subfields, list):
            continue
        merged: dict[str, str] = {}
        for sub in subfields:
            if isinstance(sub, dict):
                for code, val in sub.items():
                    if isinstance(val, str) and val.strip() and code not in merged:
                        merged[code] = val.strip()
        if merged:
            results.append(merged)
    return results


def _bn_record_matches_primary_issn(bib: dict[str, Any], issn: str) -> bool:
    """Verify a Biblioteka Narodowa bib record owns *issn* as primary ISSN (022$a)."""
    kind = str(bib.get("kind") or "").strip().lower()
    if kind and kind not in ("czasopismo", "serial", "periodical", "wydawnictwo ciągłe"):
        return False

    marc_022 = _extract_marc_subfields(bib, "022")
    if marc_022:
        return any(normalize_issn(sf.get("a")) == issn for sf in marc_022 if sf.get("a"))

    raw_isbn_issn = bib.get("isbnIssn")
    if isinstance(raw_isbn_issn, str) and raw_isbn_issn.strip():
        return normalize_issn(raw_isbn_issn) == issn

    return True


def _extract_bn_title_and_publisher(bib: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract clean serial title (MARC 245/222) and publisher (MARC 260/264) from a BN bib."""
    clean_title: str | None = None
    marc_245 = _extract_marc_subfields(bib, "245")
    if marc_245:
        sf = marc_245[0]
        parts = [_clean_marc_title(sf[k]) for k in ("a", "p") if sf.get(k)]
        joined = " ".join(p for p in parts if p).strip()
        if joined:
            clean_title = joined

    if not clean_title:
        marc_222 = _extract_marc_subfields(bib, "222")
        if marc_222:
            sf = marc_222[0]
            if sf.get("a"):
                clean_title = _clean_marc_title(sf["a"])

    if not clean_title:
        raw_title = bib.get("title")
        if isinstance(raw_title, str) and raw_title.strip():
            clean_title = _clean_marc_title(raw_title)

    clean_publisher: str | None = None
    for tag in ("264", "260"):
        marc_pub = _extract_marc_subfields(bib, tag)
        if marc_pub and marc_pub[0].get("b"):
            clean_publisher = marc_pub[0]["b"].strip().rstrip(" ,:;.")
            break

    if not clean_publisher:
        raw_pub = bib.get("publisher") or bib.get("placeOfPublication")
        if isinstance(raw_pub, str) and raw_pub.strip():
            clean_publisher = raw_pub.strip().rstrip(" ,:;.")

    return clean_title, clean_publisher


def _fetch_biblioteka_narodowa_by_issn(issn: str) -> dict[str, Any] | None:
    """Query Poland's Biblioteka Narodowa Linked Data JSON API by ISSN."""
    try:
        resp = safe_get(
            "https://data.bn.org.pl/api/institutions/bibs.json",
            params={"isbnIssn": issn, "kind": "czasopismo", "limit": "10"},
            timeout=_HTTP_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        payload = resp.json()
        bibs = payload.get("bibs") if isinstance(payload, dict) else None
        if not isinstance(bibs, list) or not bibs:
            return None
        for bib in bibs:
            if not isinstance(bib, dict) or not _bn_record_matches_primary_issn(bib, issn):
                continue
            clean_title, clean_publisher = _extract_bn_title_and_publisher(bib)
            if clean_title:
                meta: dict[str, Any] = {
                    "title": clean_title,
                    "Title": clean_title,
                    "issn": issn,
                    "work_kind": "serial",
                    "format": MediaFormat.MAGAZINE,
                    "format_type": MediaFormat.MAGAZINE,
                    "category": MediaCategory.TEXT,
                    "data_source": "biblioteka_narodowa",
                }
                if clean_publisher:
                    meta["publisher"] = clean_publisher
                if isinstance(bib.get("language"), str) and bib["language"].strip():
                    meta["language"] = bib["language"].strip().lower()[:10]
                return meta
    except (requests.RequestException, SSRFError, ValueError, KeyError, TypeError) as exc:
        logger.debug("Biblioteka Narodowa ISSN lookup failed for %s: %s", issn, exc)
    return None


def _fetch_crossref_journal_by_issn(issn: str) -> dict[str, Any] | None:
    """Query Crossref /journals/{issn} REST endpoint for serial metadata."""
    try:
        resp = safe_get(f"https://api.crossref.org/journals/{issn}", timeout=_HTTP_TIMEOUT)
        if resp.status_code != 200:
            return None
        payload = resp.json()
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, dict):
            return None
        raw_title = message.get("title")
        if isinstance(raw_title, list):
            raw_title = raw_title[0] if raw_title else None
        if not isinstance(raw_title, str) or not raw_title.strip():
            return None

        clean_title = raw_title.strip()
        meta: dict[str, Any] = {
            "title": clean_title,
            "Title": clean_title,
            "issn": issn,
            "work_kind": "serial",
            "format": MediaFormat.MAGAZINE,
            "format_type": MediaFormat.MAGAZINE,
            "category": MediaCategory.TEXT,
            "data_source": "crossref",
        }
        publisher = message.get("publisher")
        if isinstance(publisher, str) and publisher.strip():
            meta["publisher"] = publisher.strip()
        return meta
    except (requests.RequestException, SSRFError, ValueError, KeyError, TypeError) as exc:
        logger.debug("Crossref journal lookup failed for %s: %s", issn, exc)
    return None


def _fetch_openlibrary_by_issn(issn: str) -> dict[str, Any] | None:
    """Query OpenLibrary search API by ISSN."""
    try:
        resp = safe_get(
            "https://openlibrary.org/search.json",
            params={"q": f"issn:{issn}", "limit": "5"},
            timeout=_HTTP_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        payload = resp.json()
        docs = payload.get("docs") if isinstance(payload, dict) else None
        if not isinstance(docs, list) or not docs:
            return None
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            title = doc.get("title")
            if isinstance(title, str) and title.strip():
                clean_title = title.strip()
                meta: dict[str, Any] = {
                    "title": clean_title,
                    "Title": clean_title,
                    "issn": issn,
                    "work_kind": "serial",
                    "format": MediaFormat.MAGAZINE,
                    "format_type": MediaFormat.MAGAZINE,
                    "category": MediaCategory.TEXT,
                    "data_source": "openlibrary",
                }
                publishers = doc.get("publisher")
                if isinstance(publishers, list) and publishers and isinstance(publishers[0], str):
                    meta["publisher"] = publishers[0].strip()
                langs = doc.get("language")
                if isinstance(langs, list) and langs and isinstance(langs[0], str):
                    meta["language"] = langs[0].strip().lower()[:10]
                return meta
    except (requests.RequestException, SSRFError, ValueError, KeyError, TypeError) as exc:
        logger.debug("OpenLibrary ISSN lookup failed for %s: %s", issn, exc)
    return None


class SerialLookupStrategy(LookupStrategy):
    """ISSN / GS1 977 periodical lookup waterfall across BN, Crossref, OpenLibrary, and Allegro."""

    def lookup(self, barcode: str, query: str | None = None) -> tuple[dict | None, str | None]:
        """Resolve serial Work / issue metadata without fabricating absent issue details."""
        parsed = parse_issn_or_977(barcode)
        issn = parsed["issn"] if parsed else normalize_issn(barcode)
        if not issn and query:
            parsed_q = parse_issn_or_977(query)
            issn = parsed_q["issn"] if parsed_q else normalize_issn(query)

        resolved_meta: dict[str, Any] | None = None
        provider_name: str | None = None

        if issn:
            try:
                from flask import has_app_context

                if has_app_context():
                    from sqlalchemy import select

                    from app.db.models import Work, db

                    existing_work = db.session.execute(select(Work).where(Work.issn == issn)).scalars().first()
                    if existing_work is not None:
                        w_meta = existing_work.meta if isinstance(existing_work.meta, dict) else {}
                        resolved_meta = {
                            "title": existing_work.title,
                            "Title": existing_work.title,
                            "issn": issn,
                            "work_kind": existing_work.work_kind or "serial",
                            "format": MediaFormat.MAGAZINE,
                            "format_type": MediaFormat.MAGAZINE,
                            "category": MediaCategory.TEXT,
                            "data_source": "database",
                        }
                        if w_meta.get("publisher"):
                            resolved_meta["publisher"] = w_meta["publisher"]
                        provider_name = "database"
            except (ImportError, RuntimeError):
                pass

        if not resolved_meta and issn:
            for fetcher, prov in (
                (_fetch_biblioteka_narodowa_by_issn, "biblioteka_narodowa"),
                (_fetch_crossref_journal_by_issn, "crossref"),
                (_fetch_openlibrary_by_issn, "openlibrary"),
            ):
                resolved_meta = fetcher(issn)
                if resolved_meta:
                    provider_name = prov
                    break

        if not resolved_meta:
            allegro_query = parsed["ean"] if parsed and parsed.get("ean") else (barcode or query or "")
            if allegro_query:
                try:
                    allegro_meta = fetch_allegro_metadata(allegro_query)
                    if isinstance(allegro_meta, dict) and (allegro_meta.get("title") or allegro_meta.get("Title")):
                        resolved_meta = dict(allegro_meta)
                        resolved_meta["work_kind"] = "serial"
                        resolved_meta["format"] = MediaFormat.MAGAZINE
                        resolved_meta["format_type"] = MediaFormat.MAGAZINE
                        resolved_meta["category"] = MediaCategory.TEXT
                        if issn:
                            resolved_meta["issn"] = issn
                        provider_name = "allegro"
                except (requests.RequestException, ValueError, KeyError, TypeError, RuntimeError) as exc:
                    logger.debug("Allegro serial fallback failed for %s: %s", allegro_query, exc)

        if not resolved_meta:
            return None, None

        if parsed:
            if parsed.get("ean"):
                resolved_meta.setdefault("ean", parsed["ean"])
            if parsed.get("ean_addon"):
                resolved_meta["ean_addon"] = parsed["ean_addon"]
            if parsed.get("full_barcode"):
                resolved_meta["full_barcode"] = parsed["full_barcode"]
                resolved_meta["barcode"] = parsed["full_barcode"]
            elif parsed.get("ean"):
                resolved_meta.setdefault("barcode", parsed["ean"])
            if parsed.get("addon_issue_hint") is not None:
                resolved_meta.setdefault("issue_number", str(parsed["addon_issue_hint"]))

        return resolved_meta, provider_name
