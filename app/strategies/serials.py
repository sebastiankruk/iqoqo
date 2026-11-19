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
    return raw_title.strip().rstrip(" /:;.")


def _fetch_biblioteka_narodowa_by_issn(issn: str) -> dict[str, Any] | None:
    """Query Poland's Biblioteka Narodowa Linked Data JSON API by ISSN."""
    try:
        resp = safe_get(
            "https://data.bn.org.pl/api/institutions/bibs.json",
            params={"issn": issn, "limit": "5"},
            timeout=_HTTP_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        payload = resp.json()
        bibs = payload.get("bibs") if isinstance(payload, dict) else None
        if not isinstance(bibs, list) or not bibs:
            return None
        for bib in bibs:
            if not isinstance(bib, dict):
                continue
            title = bib.get("title")
            if isinstance(title, str) and title.strip():
                publisher = bib.get("publisher") or bib.get("placeOfPublication")
                clean_title = _clean_marc_title(title)
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
                if isinstance(publisher, str) and publisher.strip():
                    meta["publisher"] = publisher.strip().rstrip(" ,:;.")
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
