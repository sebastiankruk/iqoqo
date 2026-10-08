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
"""Linked Open Data (LOD) entity linking and ETL reconciliation service.

Resolves bibliographic catalog entities (Works, Manifestations, Contributors)
against external LOD authorities (DBpedia, GeoNames, WordNet) with strict
FRBR scoping and Redis caching.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from typing import Any, cast

import requests
from sqlalchemy import select

from app.core.cache import cache
from app.db import db
from app.db.core import Manifestation, SemanticLink, Work

logger = logging.getLogger(__name__)

USER_AGENT = "iqoqo/0.8.2 (https://iqoqo.org; dev@kruk.me)"
DEFAULT_REQUEST_TIMEOUT = 3.0
CACHE_TTL_24H = 86400  # 24 hours in seconds

MEDIA_CATEGORY_DBO_MAP: dict[str, str] = {
    "book": "dbo:Book",
    "text": "dbo:Book",
    "audiobook": "dbo:Book",
    "audio": "dbo:MusicalWork",
    "music": "dbo:MusicalWork",
    "sound": "dbo:MusicalWork",
    "boardgame": "dbo:Game",
    "board_game": "dbo:Game",
    "game": "dbo:Game",
    "videogame": "dbo:VideoGame",
    "movie": "dbo:Film",
    "video": "dbo:Film",
}

LOCAL_WORDNET_MAPPINGS: dict[str, dict[str, Any]] = {
    "fiction": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06362953-n",
        "label": "fiction",
        "synset_id": "06362953-n",
        "confidence": 0.95,
    },
    "non-fiction": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06363384-n",
        "label": "non-fiction",
        "synset_id": "06363384-n",
        "confidence": 0.95,
    },
    "fantasy": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06382980-n",
        "label": "fantasy",
        "synset_id": "06382980-n",
        "confidence": 0.95,
    },
    "science fiction": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06363630-n",
        "label": "science fiction",
        "synset_id": "06363630-n",
        "confidence": 0.95,
    },
    "sci-fi": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06363630-n",
        "label": "science fiction",
        "synset_id": "06363630-n",
        "confidence": 0.95,
    },
    "mystery": {
        "uri": "http://wordnet-rdf.princeton.edu/id/05820469-n",
        "label": "mystery",
        "synset_id": "05820469-n",
        "confidence": 0.95,
    },
    "horror": {
        "uri": "http://wordnet-rdf.princeton.edu/id/07530663-n",
        "label": "horror",
        "synset_id": "07530663-n",
        "confidence": 0.95,
    },
    "biography": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06443360-n",
        "label": "biography",
        "synset_id": "06443360-n",
        "confidence": 0.95,
    },
    "history": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06514774-n",
        "label": "history",
        "synset_id": "06514774-n",
        "confidence": 0.95,
    },
    "philosophy": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06159496-n",
        "label": "philosophy",
        "synset_id": "06159496-n",
        "confidence": 0.95,
    },
    "poetry": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06364024-n",
        "label": "poetry",
        "synset_id": "06364024-n",
        "confidence": 0.95,
    },
    "music": {
        "uri": "http://wordnet-rdf.princeton.edu/id/07020895-n",
        "label": "music",
        "synset_id": "07020895-n",
        "confidence": 0.95,
    },
    "art": {
        "uri": "http://wordnet-rdf.princeton.edu/id/00938676-n",
        "label": "art",
        "synset_id": "00938676-n",
        "confidence": 0.95,
    },
    "board game": {
        "uri": "http://wordnet-rdf.princeton.edu/id/00492818-n",
        "label": "board game",
        "synset_id": "00492818-n",
        "confidence": 0.95,
    },
    "adventure": {
        "uri": "http://wordnet-rdf.princeton.edu/id/00791448-n",
        "label": "adventure",
        "synset_id": "00791448-n",
        "confidence": 0.95,
    },
    "thriller": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06612712-n",
        "label": "thriller",
        "synset_id": "06612712-n",
        "confidence": 0.95,
    },
    "romance": {
        "uri": "http://wordnet-rdf.princeton.edu/id/06364539-n",
        "label": "romance",
        "synset_id": "06364539-n",
        "confidence": 0.95,
    },
}


def is_lod_linking_enabled() -> bool:
    """Check if LOD linking is enabled via configuration or environment."""
    env_val = os.environ.get("ENABLE_LOD_LINKING", "true").lower()
    return env_val in ("1", "true", "yes")


class DBpediaClient:
    """Client for resolving DBpedia resources using Lookup API and SPARQL fallback."""

    LOOKUP_URL = "https://lookup.dbpedia.org/api/search"
    SPARQL_URL = "https://dbpedia.org/sparql"

    @classmethod
    def resolve_work(
        cls,
        title: str,
        media_category: str | None = None,
        author: str | None = None,
    ) -> dict[str, Any] | None:
        """Resolve a creative work by title, media category class, and author context."""
        if not title:
            return None

        normalized_title = title.strip()
        dbo_type = MEDIA_CATEGORY_DBO_MAP.get((media_category or "").lower())
        cache_key = f"lod:dbpedia:work:{normalized_title.lower()}:{dbo_type or 'all'}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        # Step 1: Query DBpedia Lookup API
        result = cls._query_lookup(normalized_title, type_name=dbo_type)

        # Fallback 1b: If title has subtitle or parenthetical comment, retry with main title
        if not result:
            clean_title = re.sub(r"\(.*?\)", "", normalized_title).strip()
            if ":" in clean_title:
                clean_title = clean_title.split(":", 1)[0].strip()
            elif " - " in clean_title:
                clean_title = clean_title.split(" - ", 1)[0].strip()
            if clean_title and clean_title != normalized_title:
                result = cls._query_lookup(clean_title, type_name=dbo_type)

        # Step 2: Fallback to SPARQL if lookup yields nothing
        if not result and dbo_type:
            result = cls._query_sparql(normalized_title, dbo_type=dbo_type)

        # Cache result (including None to prevent repeated failed queries)
        cache.set(cache_key, result, timeout=CACHE_TTL_24H)
        return result

    @classmethod
    def resolve_person(cls, name: str) -> dict[str, Any] | None:
        """Resolve a person (author, artist, contributor) on DBpedia."""
        if not name:
            return None

        normalized_name = name.strip()
        cache_key = f"lod:dbpedia:person:{normalized_name.lower()}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        result = cls._query_lookup(normalized_name, type_name="Person")
        if not result:
            result = cls._query_sparql(normalized_name, dbo_type="dbo:Person")

        cache.set(cache_key, result, timeout=CACHE_TTL_24H)
        return result

    @classmethod
    def _query_lookup(cls, query: str, type_name: str | None = None) -> dict[str, Any] | None:
        """Execute query against DBpedia Lookup API."""
        lookup_type = type_name.split(":")[-1] if type_name else None
        params: dict[str, Any] = {"query": query, "maxResults": 5, "format": "json"}
        if lookup_type:
            params["typeName"] = lookup_type

        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }

        try:
            resp = requests.get(cls.LOOKUP_URL, params=params, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            if resp.status_code != 200:
                logger.warning("DBpedia Lookup returned status %d for query %s", resp.status_code, query)
                return None

            data = resp.json()
            docs = data.get("docs", [])
            if not docs:
                return None

            first = docs[0]
            # Handle list vs scalar values from DBpedia Lookup JSON schema
            res_val = first.get("resource")
            uri = res_val[0] if isinstance(res_val, list) and res_val else res_val
            label_val = first.get("label")
            label = label_val[0] if isinstance(label_val, list) and label_val else (label_val or query)

            if not uri:
                return None

            # Calculate confidence score
            score_val = first.get("score")
            score_num = score_val[0] if isinstance(score_val, list) and score_val else score_val
            confidence = min(0.95, max(0.60, float(score_num) / 100.0)) if score_num else 0.85

            comment_val = first.get("comment", [""])[0] if isinstance(first.get("comment"), list) else (first.get("comment") or "")

            return {
                "uri": uri,
                "label": re.sub(r"<[^>]+>", "", str(label)),
                "confidence": round(confidence, 2),
                "strategy": "lookup",
                "attributes": {
                    "dbo_type": type_name,
                    "comment": re.sub(r"<[^>]+>", "", str(comment_val)),
                },
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("DBpedia Lookup request failed for query %s: %s", query, exc)
            return None

    @classmethod
    def _query_sparql(cls, query: str, dbo_type: str) -> dict[str, Any] | None:
        """Targeted SPARQL fallback query on DBpedia using full-text and literal indexing."""
        clean_words = re.sub(r"[^\w\s]", " ", query).strip().split()
        if not clean_words:
            return None
        fts_clause = " AND ".join(f"'{w}'" for w in clean_words)

        sparql_query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?res ?label WHERE {{
          ?res a {dbo_type} ;
               rdfs:label ?label .
          ?label bif:contains "{fts_clause}" .
          FILTER(lang(?label) = "en" || lang(?label) = "pl" || lang(?label) = "")
        }} LIMIT 1
        """
        params = {"query": sparql_query, "format": "json"}
        headers = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}

        try:
            resp = requests.get(cls.SPARQL_URL, params=params, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            if resp.status_code != 200:
                return None

            bindings = resp.json().get("results", {}).get("bindings", [])
            if not bindings:
                return None

            b = bindings[0]
            uri = b.get("res", {}).get("value")
            label = b.get("label", {}).get("value", query)

            if not uri:
                return None

            return {
                "uri": uri,
                "label": label,
                "confidence": 0.80,
                "strategy": "sparql",
                "attributes": {"dbo_type": dbo_type},
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("DBpedia SPARQL query failed for %s: %s", query, exc)
            return None


class GeoNamesClient:
    """Client for resolving geographic locations and publisher cities against GeoNames."""

    SEARCH_URL = "https://secure.geonames.org/searchJSON"
    DEFAULT_DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "geonames_cities.db",
    )

    @classmethod
    def _resolve_local(cls, location_name: str) -> dict[str, Any] | None:
        """Resolve location against local offline SQLite gazetteer."""
        db_path = os.environ.get("GEONAMES_DB_PATH") or cls.DEFAULT_DB_PATH
        if not os.path.exists(db_path):
            return None

        clean_name = location_name.strip().lower()
        if not clean_name:
            return None

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            # Attempt 1: Direct match on official name or asciiname
            query_direct = """
            SELECT geoname_id, name, country_code, lat, lng, fcode, population
            FROM cities
            WHERE LOWER(name) = ? OR LOWER(asciiname) = ?
            ORDER BY population DESC
            LIMIT 1;
            """
            cursor.execute(query_direct, (clean_name, clean_name))
            row = cursor.fetchone()

            # Attempt 2: Match via international alternate names table
            if not row:
                query_alt = """
                SELECT c.geoname_id, c.name, c.country_code, c.lat, c.lng, c.fcode, c.population
                FROM alt_names a
                JOIN cities c ON a.geoname_id = c.geoname_id
                WHERE a.name_lower = ?
                ORDER BY c.population DESC
                LIMIT 1;
                """
                cursor.execute(query_alt, (clean_name,))
                row = cursor.fetchone()

            conn.close()

            if not row:
                return None

            gid, name, country_code, lat, lng, fcode, _pop = row
            uri = f"https://sws.geonames.org/{gid}/"
            return {
                "uri": uri,
                "label": name,
                "confidence": 0.95,
                "strategy": "local_gazetteer",
                "attributes": {
                    "geoname_id": gid,
                    "name": name,
                    "country_code": country_code,
                    "lat": float(lat) if lat is not None else None,
                    "lng": float(lng) if lng is not None else None,
                    "fcode": fcode,
                },
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Local GeoNames gazetteer query failed for %s: %s", location_name, exc)
            return None

    @classmethod
    def resolve_location(cls, location_name: str) -> dict[str, Any] | None:
        """Resolve a city or place string to a canonical GeoNames URI."""
        if not location_name:
            return None

        normalized = location_name.strip()
        cache_key = f"lod:geonames:{normalized.lower()}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        # Priority 1: Check local offline gazetteer (0ms, no network, no auth)
        local_result = cls._resolve_local(normalized)
        if local_result:
            cache.set(cache_key, local_result, timeout=CACHE_TTL_24H)
            return local_result

        # Priority 2: Fallback to remote GeoNames API if credentials exist
        db_user = None
        try:
            from app.db.settings import InstanceSettings

            db_user = InstanceSettings.get_value("GEONAMES_USERNAME")
        except Exception:  # pylint: disable=broad-except
            pass
        username = (db_user or "").strip() or os.environ.get("GEONAMES_USERNAME", "iqoqo_demo")
        params: dict[str, Any] = {
            "q": normalized,
            "maxRows": 1,
            "username": username,
            "style": "FULL",
        }
        headers = {"User-Agent": USER_AGENT}

        result: dict[str, Any] | None = None
        try:
            resp = requests.get(cls.SEARCH_URL, params=params, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if "status" in data:
                    logger.warning(
                        "GeoNames API returned error for %s: %s (code %s)",
                        location_name,
                        data["status"].get("message"),
                        data["status"].get("value"),
                    )
                else:
                    geonames = data.get("geonames", [])
                    if geonames:
                        g = geonames[0]
                        gid = g.get("geonameId")
                        if gid:
                            uri = f"https://sws.geonames.org/{gid}/"
                            lat = float(g.get("lat")) if g.get("lat") else None
                            lng = float(g.get("lng")) if g.get("lng") else None
                            country_code = g.get("countryCode")
                            name = g.get("name", normalized)

                            result = {
                                "uri": uri,
                                "label": name,
                                "confidence": 0.90,
                                "strategy": "lookup",
                                "attributes": {
                                    "geoname_id": gid,
                                    "name": name,
                                    "country_code": country_code,
                                    "lat": lat,
                                    "lng": lng,
                                    "fcode": g.get("fcode"),
                                },
                            }
            else:
                logger.warning("GeoNames request returned HTTP %d for location %s", resp.status_code, location_name)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("GeoNames request failed for location %s: %s", location_name, exc)
            result = None

        if result:
            cache.set(cache_key, result, timeout=CACHE_TTL_24H)
        return result


class WordNetMapper:
    """Maps subject, genre, and topical tags to canonical WordNet synset URIs."""

    @classmethod
    def resolve_tag(cls, tag: str) -> dict[str, Any] | None:
        """Resolve a tag to a WordNet synset URI via local dictionary or DBpedia category fallback."""
        if not tag:
            return None

        normalized = tag.strip().lower()
        cache_key = f"lod:wordnet:{normalized}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        result: dict[str, Any] | None = None

        # 1. Local dictionary lookup (instant, zero network latency)
        if normalized in LOCAL_WORDNET_MAPPINGS:
            entry = LOCAL_WORDNET_MAPPINGS[normalized]
            result = {
                "uri": entry["uri"],
                "label": entry["label"],
                "confidence": entry["confidence"],
                "authority": "wordnet",
                "strategy": "synset",
                "attributes": {
                    "synset_id": entry["synset_id"],
                    "source": "local_dictionary",
                },
            }
            cache.set(cache_key, result, timeout=CACHE_TTL_24H)
            return result

        # 2. Fallback to DBpedia category / synset concept
        result = cls._resolve_dbpedia_category(tag.strip())
        cache.set(cache_key, result, timeout=CACHE_TTL_24H)
        return result

    @classmethod
    def _validate_dbpedia_category(cls, uri: str) -> bool:
        """Validate that the DBpedia Category exists using HTTP HEAD/GET."""
        try:
            resp = requests.head(
                uri,
                headers={"User-Agent": USER_AGENT},
                timeout=2.0,
                allow_redirects=True,
            )
            if resp.status_code in (200, 303):
                return True
            if resp.status_code == 405:
                resp = requests.get(
                    uri,
                    headers={"User-Agent": USER_AGENT, "Accept": "application/rdf+xml, text/html"},
                    timeout=2.0,
                    allow_redirects=True,
                )
                return resp.status_code in (200, 303)
            return False
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("DBpedia category validation failed for %s: %s", uri, exc)
            return False

    @classmethod
    def _resolve_dbpedia_category(cls, tag: str) -> dict[str, Any] | None:
        """Query DBpedia for a matching Category / Concept for novel tags."""
        formatted_tag = "_".join(word.capitalize() for word in tag.split())
        uri = f"http://dbpedia.org/resource/Category:{formatted_tag}"

        if not cls._validate_dbpedia_category(uri):
            return None

        return {
            "uri": uri,
            "label": tag,
            "confidence": 0.70,
            "authority": "dbpedia",
            "strategy": "dbpedia_category",
            "attributes": {"source": "dbpedia_category_fallback"},
        }


def resolve_manifestation_links(manifestation_id: int) -> list[SemanticLink]:
    """
    Resolve and persist Linked Open Data links for a Manifestation and its parent Work.

    Strict FRBR Scoping Rules:
    - Work (F1): DBpedia creative work entity, author persons, WordNet synsets/topics.
    - Manifestation (F3): GeoNames publication places, publisher entities, format URIs.
    - Item (F4): Separated from abstract catalog links; items inherit via manifestation.
    """
    if not is_lod_linking_enabled():
        logger.info("LOD linking is disabled, skipping manifestation %d", manifestation_id)
        return []

    manifestation = db.session.get(Manifestation, manifestation_id)
    if not manifestation:
        logger.warning("Manifestation %d not found for LOD resolution", manifestation_id)
        return []

    created_links: list[SemanticLink] = []

    # -------------------------------------------------------------------------
    # 1. Work-Level Resolutions (F1)
    # -------------------------------------------------------------------------
    work: Work | None = None
    if manifestation.expression and manifestation.expression.work:
        work = manifestation.expression.work

    if work:
        media_cat = (
            getattr(manifestation, "media_category", None)
            or (work.meta.get("media_category") if work.meta else None)
            or (manifestation.expression.content_type if manifestation.expression and manifestation.expression.content_type else None)
            or (manifestation.format_type if manifestation.format_type else None)
        )

        # 1a. DBpedia Work Resolution
        work_match = DBpediaClient.resolve_work(
            title=work.title,
            media_category=media_cat,
            author=manifestation.author,
        )
        if work_match:
            existing = db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "work",
                    SemanticLink.entity_id == work.id,
                    SemanticLink.authority == "dbpedia",
                    SemanticLink.external_uri == work_match["uri"],
                )
            ).scalar_one_or_none()

            if not existing:
                link = SemanticLink(
                    entity_type="work",
                    entity_id=work.id,
                    authority="dbpedia",
                    external_uri=work_match["uri"],
                    pref_label=work_match["label"],
                    confidence=work_match["confidence"],
                    match_strategy=work_match["strategy"],
                    attributes=work_match["attributes"],
                    verified=False,
                )
                db.session.add(link)
                created_links.append(link)

        # 1b. DBpedia Author / Contributor Resolution
        authors: list[str] = []
        if work.meta and isinstance(work.meta.get("authors"), list):
            authors.extend([a for a in work.meta["authors"] if isinstance(a, str)])
        elif manifestation.author:
            authors.append(manifestation.author)

        for author_name in authors[:3]:  # Resolve up to 3 authors to respect rate limits
            author_match = DBpediaClient.resolve_person(author_name)
            if author_match:
                existing_author = db.session.execute(
                    select(SemanticLink).where(
                        SemanticLink.entity_type == "work",
                        SemanticLink.entity_id == work.id,
                        SemanticLink.authority == "dbpedia",
                        SemanticLink.external_uri == author_match["uri"],
                    )
                ).scalar_one_or_none()

                if not existing_author:
                    author_link = SemanticLink(
                        entity_type="work",
                        entity_id=work.id,
                        authority="dbpedia",
                        external_uri=author_match["uri"],
                        pref_label=author_match["label"],
                        confidence=author_match["confidence"],
                        match_strategy=author_match["strategy"],
                        attributes={**author_match["attributes"], "role": "author"},
                        verified=False,
                    )
                    db.session.add(author_link)
                    created_links.append(author_link)

        # 1c. WordNet Subject / Genre Tag Resolutions
        tags: list[str] = []
        if work.meta:
            for field in ("subjects", "genres", "tags"):
                val = work.meta.get(field)
                if isinstance(val, list):
                    tags.extend([str(t) for t in val if isinstance(t, str)])
                elif isinstance(val, str):
                    tags.append(val)

        for tag in tags[:5]:  # Reconcile up to 5 topical tags
            wn_match = WordNetMapper.resolve_tag(tag)
            if wn_match:
                authority = wn_match.get("authority", "wordnet")
                existing_wn = db.session.execute(
                    select(SemanticLink).where(
                        SemanticLink.entity_type == "work",
                        SemanticLink.entity_id == work.id,
                        SemanticLink.authority == authority,
                        SemanticLink.external_uri == wn_match["uri"],
                    )
                ).scalar_one_or_none()

                if not existing_wn:
                    wn_link = SemanticLink(
                        entity_type="work",
                        entity_id=work.id,
                        authority=authority,
                        external_uri=wn_match["uri"],
                        pref_label=wn_match["label"],
                        confidence=wn_match["confidence"],
                        match_strategy=wn_match["strategy"],
                        attributes=wn_match["attributes"],
                        verified=False,
                    )
                    db.session.add(wn_link)
                    created_links.append(wn_link)

    # -------------------------------------------------------------------------
    # 2. Manifestation-Level Resolutions (F3)
    # -------------------------------------------------------------------------
    pub_place = None
    if manifestation.meta:
        pub_place = (
            manifestation.meta.get("publication_place") or manifestation.meta.get("publish_places") or manifestation.meta.get("city")
        )
        if isinstance(pub_place, list) and pub_place:
            pub_place = pub_place[0]

    if pub_place and isinstance(pub_place, str):
        geo_match = GeoNamesClient.resolve_location(pub_place)
        if geo_match:
            existing_geo = db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "manifestation",
                    SemanticLink.entity_id == manifestation.id,
                    SemanticLink.authority == "geonames",
                    SemanticLink.external_uri == geo_match["uri"],
                )
            ).scalar_one_or_none()

            if not existing_geo:
                geo_link = SemanticLink(
                    entity_type="manifestation",
                    entity_id=manifestation.id,
                    authority="geonames",
                    external_uri=geo_match["uri"],
                    pref_label=geo_match["label"],
                    confidence=geo_match["confidence"],
                    match_strategy=geo_match["strategy"],
                    attributes=geo_match["attributes"],
                    verified=False,
                )
                db.session.add(geo_link)
                created_links.append(geo_link)

    if created_links:
        db.session.commit()

    return created_links


def get_manifestation_semantic_links_dict(manifestation_id: int) -> dict[str, Any]:
    """Retrieve and group semantic links for a manifestation and its parent work."""
    manifestation = db.session.get(Manifestation, manifestation_id)
    if not manifestation:
        return {"manifestation_id": manifestation_id, "links": [], "grouped": {}}

    all_links = manifestation.get_semantic_links(include_work=True)
    serialized = [link.to_dict() for link in all_links]

    grouped: dict[str, list[dict[str, Any]]] = {
        "dbpedia": [],
        "geonames": [],
        "wordnet": [],
    }
    for item in serialized:
        auth = item.get("authority", "other")
        grouped.setdefault(auth, []).append(item)

    return {
        "manifestation_id": manifestation_id,
        "total": len(serialized),
        "links": serialized,
        "grouped": grouped,
    }
