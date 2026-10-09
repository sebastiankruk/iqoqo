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
from difflib import SequenceMatcher
from typing import Any, cast

import requests
from sqlalchemy import select

from app.core.cache import cache
from app.core.config_service import ConfigService
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

GEONAMES_TITLE_STOPWORDS: set[str] = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "into",
    "onto",
    "upon",
    "about",
    "above",
    "after",
    "before",
    "between",
    "under",
    "over",
    "through",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "can",
    "could",
    "shall",
    "should",
    "will",
    "would",
    "may",
    "might",
    "must",
    "this",
    "that",
    "these",
    "those",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
    "who",
    "whom",
    "whose",
    "which",
    "what",
    "where",
    "when",
    "why",
    "how",
    "not",
    "no",
    "nor",
    "all",
    "any",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "than",
    "too",
    "very",
    "just",
    "now",
    "then",
    "here",
    "there",
    "book",
    "books",
    "guide",
    "guides",
    "handbook",
    "pocket",
    "manual",
    "intro",
    "introduction",
    "illustrated",
    "edition",
    "series",
    "volume",
    "vol",
    "part",
    "chapter",
    "story",
    "stories",
    "novel",
    "tales",
    "tale",
    "complete",
    "essential",
    "essentials",
    "best",
    "great",
    "world",
    "life",
    "day",
    "days",
    "time",
    "times",
    "year",
    "years",
    "future",
    "history",
    "biography",
    "memoir",
    "memoirs",
    "notes",
    "journal",
    "review",
    "press",
    "media",
    "house",
    "group",
    "publishing",
    "publications",
    "paperback",
    "paperbacks",
    "hardcover",
    "classics",
    "trade",
    "company",
    "limited",
    "ltd",
    "inc",
    "corp",
    "corporation",
    "international",
    "travel",
    "travels",
    "city",
    "cities",
    "town",
    "map",
    "maps",
    "man",
    "men",
    "woman",
    "women",
    "child",
    "children",
    "people",
    "love",
    "war",
    "peace",
    "dark",
    "light",
    "secret",
    "secrets",
    "lost",
    "found",
    "shadow",
    "wind",
    "water",
    "fire",
    "earth",
    "sky",
    "sun",
    "moon",
    "star",
    "stars",
    "sea",
    "ocean",
    "river",
    "mountain",
    "hill",
    "road",
    "street",
    "way",
    "home",
    "room",
    "first",
    "second",
    "third",
    "last",
    "new",
    "old",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "out",
    "up",
    "down",
    "off",
    "good",
    "bad",
    "big",
    "small",
    "little",
    "read",
    "reading",
    "write",
    "writing",
    "learn",
    "learning",
    "art",
    "music",
    "play",
    "game",
    "games",
    "fall",
    "spring",
    "summer",
    "winter",
    "york",
    "turbo",
    "male",
    "dla",
    "nas",
    "gra",
    "pod",
    "nad",
    "nie",
    "tak",
    "pan",
    "pani",
    "jak",
    "jako",
    "albo",
    "oraz",
    "lecz",
    "jego",
    "jej",
    "ich",
    "tym",
    "tam",
    "tu",
    "franklin",
    "anna",
    "martin",
    "david",
    "george",
    "mary",
    "michael",
    "bryan",
    "austin",
    "wilson",
    "jackson",
    "dolores",
    "theodore",
    "mark",
    "marka",
    "roman",
    "peter",
    "paul",
    "john",
    "james",
    "robert",
    "william",
    "thomas",
    "richard",
    "charles",
    "joseph",
    "daniel",
    "matthew",
    "anthony",
    "donald",
    "steven",
    "andrew",
    "edward",
    "joshua",
    "brian",
    "kevin",
    "ronald",
    "timothy",
    "jason",
    "jeffrey",
    "ryan",
    "gary",
    "jacob",
    "nicholas",
    "eric",
    "jonathan",
    "stephen",
    "larry",
    "justin",
    "scott",
    "brandon",
    "benjamin",
    "samuel",
    "frank",
    "gregory",
    "raymond",
    "alexander",
    "patrick",
    "jack",
    "dennis",
    "jerry",
    "tyler",
    "aaron",
    "jose",
    "adam",
    "nathan",
    "henry",
    "douglas",
    "zachary",
    "kyle",
    "walter",
    "ethan",
    "jeremy",
    "harold",
    "keith",
    "christian",
    "roger",
    "noah",
    "gerald",
    "carl",
    "terry",
    "sean",
    "arthur",
    "lawrence",
    "jesse",
    "dylan",
    "joe",
    "jordan",
    "billy",
    "bruce",
    "albert",
    "willie",
    "gabriel",
    "logan",
    "alan",
    "juan",
    "wayne",
    "roy",
    "ralph",
    "randy",
    "eugene",
    "vincent",
    "russell",
    "louis",
    "philip",
    "bobby",
    "johnny",
    "bradley",
    "harry",
    "darwin",
    "phoenix",
    "salem",
    "sunset",
    "toma",
    "linden",
    "boone",
    "sejong",
    "dire",
    "beverley",
    "santana",
    "madison",
    "nice",
    "metro",
    "oral",
    "sale",
    "samba",
    "aurora",
    "buena",
    "vista",
    "houston",
}


CREATIVE_WORK_CLASSES: set[str] = {
    "dbo:Work",
    "dbo:CreativeWork",
    "dbo:Book",
    "dbo:WrittenWork",
    "dbo:MusicalWork",
    "dbo:Game",
    "dbo:VideoGame",
    "dbo:Film",
    "dbo:Artwork",
    "Work",
    "CreativeWork",
    "Book",
    "WrittenWork",
    "MusicalWork",
    "Game",
    "VideoGame",
    "Film",
    "Artwork",
}

AGENT_CLASSES: set[str] = {
    "dbo:Person",
    "dbo:Organisation",
    "dbo:Organization",
    "dbo:Agent",
    "Person",
    "Organisation",
    "Organization",
    "Agent",
    "foaf:Person",
    "schema:Person",
    "schema:Organization",
}

DISAMBIGUATION_MARKERS: tuple[str, ...] = (
    "(disambiguation)",
    "may refer to",
    "can refer to",
    "refers to:",
    "frequently refers to",
    "commonly refers to",
    "is a disambiguation page",
    "disambiguation page",
)


def is_disambiguation(uri: str, label: str, comment: str = "") -> bool:
    """Check if a DBpedia resource is a disambiguation or list page."""
    uri_lower = uri.lower()
    label_lower = label.lower()
    comment_lower = comment.lower()

    if "(disambiguation)" in uri_lower or "(disambiguation)" in label_lower:
        return True
    if label_lower.startswith("list of "):
        return True
    for marker in DISAMBIGUATION_MARKERS:
        if marker in comment_lower:
            return True
    return False


def normalize_title_for_comparison(text: str) -> str:
    """Normalize text by stripping parentheticals, punctuation, and lowercase."""
    cleaned = re.sub(r"\(.*?\)", "", text).strip()
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    return " ".join(cleaned.lower().split())


def compute_composite_score(
    candidate_label: str,
    target_title: str,
    author: str | None = None,
    candidate_comment: str | None = None,
    year: int | None = None,
    rank_margin: float = 0.0,
    has_class_match: bool = True,
) -> float:
    """Compute multi-signal composite confidence score for an entity candidate.

    Signals:
    - Label similarity (0.50 max) via SequenceMatcher
    - Author / Contributor corroboration (0.25 max)
    - Publication year proximity (0.15 max)
    - Candidate rank margin from lookup search (0.10 max)
    """
    if not has_class_match:
        return 0.0

    comm = candidate_comment or ""
    if is_disambiguation("", candidate_label, comm):
        return 0.0

    # 1. Label similarity (0.50 max)
    norm_target = normalize_title_for_comparison(target_title)
    norm_cand = normalize_title_for_comparison(candidate_label)
    if not norm_target or not norm_cand:
        sim = 0.0
    elif norm_target == norm_cand:
        sim = 1.0
    else:
        sim = SequenceMatcher(None, norm_target, norm_cand).ratio()
    label_score = sim * 0.50

    # 2. Author / contributor corroboration (0.25 max)
    if author and author.strip():
        norm_author = author.strip().lower()
        comm_lower = comm.lower()
        if norm_author in comm_lower:
            author_score = 0.25
        else:
            tokens = [t for t in re.split(r"\s+", norm_author) if len(t) >= 3]
            if tokens and any(t in comm_lower for t in tokens):
                author_score = 0.20
            else:
                author_score = 0.0
    else:
        author_score = 0.15

    # 3. Year proximity (0.15 max)
    if year:
        found_years = [int(y) for y in re.findall(r"\b(1[789]\d\d|20\d\d)\b", comm)]
        if found_years:
            min_diff = min(abs(y - year) for y in found_years)
            if min_diff == 0:
                year_score = 0.15
            elif min_diff <= 2:
                year_score = 0.12
            elif min_diff <= 5:
                year_score = 0.08
            else:
                year_score = 0.0
        else:
            year_score = 0.08
    else:
        year_score = 0.10

    # 4. Lookup rank margin (0.10 max)
    margin_clamped = max(0.0, min(1.0, float(rank_margin)))
    margin_score = margin_clamped * 0.10

    total = label_score + author_score + year_score + margin_score
    return round(max(0.0, min(1.0, total)), 2)


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
        year: int | None = None,
        fast_mode: bool = False,
    ) -> dict[str, Any] | None:
        """Resolve a creative work by title, media category class, author, and year context."""
        if not title:
            return None

        normalized_title = title.strip()
        dbo_type = MEDIA_CATEGORY_DBO_MAP.get((media_category or "").lower()) or "dbo:Work"
        cache_key = f"lod:dbpedia:work:{normalized_title.lower()}:{dbo_type}:{author or ''}:{year or ''}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        # Step 1: Query DBpedia Lookup API
        result = cls._query_lookup(normalized_title, type_name=dbo_type, author=author, year=year)

        # Fallback 1b: If title has subtitle or parenthetical comment, retry with main title
        if not result:
            clean_title = re.sub(r"\(.*?\)", "", normalized_title).strip()
            if ":" in clean_title:
                clean_title = clean_title.split(":", 1)[0].strip()
            elif " - " in clean_title:
                clean_title = clean_title.split(" - ", 1)[0].strip()
            if clean_title and clean_title != normalized_title:
                result = cls._query_lookup(clean_title, type_name=dbo_type, author=author, year=year)

        # Step 2: Fallback to SPARQL if lookup yields nothing (skipped in fast mode)
        if not result and dbo_type and not fast_mode:
            result = cls._query_sparql(normalized_title, dbo_type=dbo_type, author=author, year=year)

        # Cache result (including None to prevent repeated failed queries)
        cache.set(cache_key, result, timeout=CACHE_TTL_24H)
        return result

    @classmethod
    def resolve_person(cls, name: str, fast_mode: bool = False) -> dict[str, Any] | None:
        """Resolve a person (author, artist, contributor) on DBpedia."""
        if not name:
            return None

        normalized_name = name.strip()
        cache_key = f"lod:dbpedia:person:{normalized_name.lower()}"

        cached = cache.get(cache_key)
        if cached is not None:
            return cast(dict[str, Any], cached)

        result = cls._query_lookup(normalized_name, type_name="Person")
        if not result and not fast_mode:
            result = cls._query_sparql(normalized_name, dbo_type="dbo:Person")

        cache.set(cache_key, result, timeout=CACHE_TTL_24H)
        return result

    @classmethod
    def _query_lookup(
        cls,
        query: str,
        type_name: str | None = None,
        author: str | None = None,
        year: int | None = None,
    ) -> dict[str, Any] | None:
        """Execute query against DBpedia Lookup API and rank candidate resources."""
        lookup_type = type_name.split(":")[-1] if type_name else None
        params: dict[str, Any] = {"query": query, "maxResults": 5, "format": "json"}
        if lookup_type:
            params["typeName"] = lookup_type
        else:
            params["typeName"] = "Work"

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

            is_agent_query = lookup_type in ("Person", "Organisation", "Organization", "Agent")
            allowed_classes = AGENT_CLASSES if is_agent_query else CREATIVE_WORK_CLASSES

            candidates: list[dict[str, Any]] = []
            for doc in docs:
                res_val = doc.get("resource")
                uri = res_val[0] if isinstance(res_val, list) and res_val else res_val
                if not uri:
                    continue

                label_val = doc.get("label")
                label = label_val[0] if isinstance(label_val, list) and label_val else (label_val or query)
                clean_label = re.sub(r"<[^>]+>", "", str(label))

                comment_val = doc.get("comment", [""])[0] if isinstance(doc.get("comment"), list) else (doc.get("comment") or "")
                clean_comment = re.sub(r"<[^>]+>", "", str(comment_val))

                if is_disambiguation(uri, clean_label, clean_comment):
                    continue

                # Ontology class validation
                doc_types = doc.get("typeName", [])
                if isinstance(doc_types, str):
                    doc_types = [doc_types]
                doc_uris = doc.get("type", [])
                if isinstance(doc_uris, str):
                    doc_uris = [doc_uris]

                all_type_strings = set(doc_types) | {u.split("/")[-1] for u in doc_uris}
                has_class_match = True
                if all_type_strings and not (all_type_strings & allowed_classes):
                    has_class_match = False

                if not has_class_match:
                    continue

                raw_score_val = doc.get("score")
                raw_score = raw_score_val[0] if isinstance(raw_score_val, list) and raw_score_val else raw_score_val
                try:
                    score_num = float(raw_score) if raw_score is not None else 0.0
                except (ValueError, TypeError):
                    score_num = 0.0

                candidates.append(
                    {
                        "uri": uri,
                        "label": clean_label,
                        "comment": clean_comment,
                        "raw_score": score_num,
                        "has_class_match": has_class_match,
                    }
                )

            if not candidates:
                return None

            first_raw = candidates[0]["raw_score"]
            second_raw = candidates[1]["raw_score"] if len(candidates) > 1 else 0.0
            rank_margin = (first_raw - second_raw) / (first_raw + 1e-6) if first_raw > 0 else 1.0

            scored_candidates: list[tuple[float, dict[str, Any]]] = []
            for cand in candidates:
                conf = compute_composite_score(
                    candidate_label=cand["label"],
                    target_title=query,
                    author=author,
                    candidate_comment=cand["comment"],
                    year=year,
                    rank_margin=rank_margin if cand == candidates[0] else 0.0,
                    has_class_match=cand["has_class_match"],
                )
                scored_candidates.append((conf, cand))

            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_cand = scored_candidates[0]

            return {
                "uri": best_cand["uri"],
                "label": best_cand["label"],
                "confidence": best_score,
                "strategy": "lookup",
                "attributes": {
                    "dbo_type": type_name or "dbo:Work",
                    "comment": best_cand["comment"],
                },
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("DBpedia Lookup request failed for query %s: %s", query, exc)
            return None

    @classmethod
    def _query_sparql(
        cls,
        query: str,
        dbo_type: str,
        author: str | None = None,
        year: int | None = None,
    ) -> dict[str, Any] | None:
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
            resp = requests.get(cls.SPARQL_URL, params=params, headers=headers, timeout=1.5)
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

            conf = compute_composite_score(
                candidate_label=label,
                target_title=query,
                author=author,
                year=year,
                rank_margin=1.0,
                has_class_match=True,
            )
            if conf < 0.80 and normalize_title_for_comparison(label) == normalize_title_for_comparison(query):
                conf = 0.80

            return {
                "uri": uri,
                "label": label,
                "confidence": conf,
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

        raw = location_name.strip()
        if not raw:
            return None

        candidates = [raw]

        # Strip parentheticals e.g. "Copenhagen (Denmark)" -> "Copenhagen"
        no_paren = re.sub(r"\(.*?\)", "", raw).strip()
        if no_paren and no_paren != raw:
            candidates.append(no_paren)

        # Split on commas e.g. "Berkeley, Calif" -> "Berkeley", "Wydawnictwo, Kraków" -> "Kraków"
        for base in (raw, no_paren):
            if "," in base:
                parts = [p.strip() for p in base.split(",") if p.strip()]
                candidates.extend(parts)

        # Split on colons e.g. "London : Penguin" -> "London"
        if ":" in raw:
            parts = [p.strip() for p in raw.split(":") if p.strip()]
            candidates.extend(parts)

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            row = None
            for cand in candidates:
                clean_name = cand.strip().lower()
                if not clean_name or len(clean_name) < 2:
                    continue

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

                if row:
                    break

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
        except (sqlite3.Error, OSError) as exc:
            logger.warning("Local GeoNames gazetteer query failed for %s: %s", location_name, exc)
            return None

    @classmethod
    def extract_locations_from_text(cls, text: str) -> list[dict[str, Any]]:
        """Extract high-precision geographic entities from title, subject, or publisher strings."""
        if not text:
            return []

        db_path = os.environ.get("GEONAMES_DB_PATH") or cls.DEFAULT_DB_PATH
        if not os.path.exists(db_path):
            return []

        tokens: list[tuple[str, int, int]] = []
        for m in re.finditer(r"\b[A-Za-zÀ-ÿ]{3,}\b", text):
            tokens.append((m.group(0), m.start(), m.end()))

        if not tokens:
            return []

        n = len(tokens)
        candidates: list[tuple[str, int, int, int]] = []
        for length in range(min(3, n), 0, -1):
            for i in range(n - length + 1):
                phrase_tokens = tokens[i : i + length]
                phrase = " ".join(t[0] for t in phrase_tokens)
                if phrase.lower() not in GEONAMES_TITLE_STOPWORDS and len(phrase) >= 4:
                    candidates.append((phrase, phrase_tokens[0][1], phrase_tokens[-1][2], length))

        candidates.sort(key=lambda x: (x[3], len(x[0])), reverse=True)

        found: list[dict[str, Any]] = []
        covered_spans: list[tuple[int, int]] = []
        seen_ids: set[int] = set()

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()

            for cand, start_pos, end_pos, cand_len in candidates:
                if any(cs <= start_pos and end_pos <= ce for cs, ce in covered_spans):
                    continue

                cand_lower = cand.lower()
                query_direct = """
                SELECT geoname_id, name, country_code, lat, lng, fcode, population
                FROM cities
                WHERE LOWER(name) = ? OR LOWER(asciiname) = ?
                ORDER BY population DESC LIMIT 1;
                """
                cursor.execute(query_direct, (cand_lower, cand_lower))
                row = cursor.fetchone()

                if not row and cand_len >= 2:
                    query_alt = """
                    SELECT c.geoname_id, c.name, c.country_code, c.lat, c.lng, c.fcode, c.population
                    FROM alt_names a
                    JOIN cities c ON a.geoname_id = c.geoname_id
                    WHERE a.name_lower = ? AND (c.population >= 100000 OR c.fcode = 'PPLC')
                    ORDER BY c.population DESC LIMIT 1;
                    """
                    cursor.execute(query_alt, (cand_lower,))
                    row = cursor.fetchone()

                if row and (row[6] >= 100000 or row[5] in ("PPLC", "PPLA", "PPLA2")):
                    if cand[0].isupper() and row[0] not in seen_ids:
                        seen_ids.add(row[0])
                        covered_spans.append((start_pos, end_pos))
                        gid, name, country_code, lat, lng, fcode, _pop = row
                        found.append(
                            {
                                "uri": f"https://sws.geonames.org/{gid}/",
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
                                    "matched_text": cand,
                                },
                            }
                        )

            conn.close()
        except (sqlite3.Error, OSError) as exc:
            logger.warning("Local GeoNames extraction failed for text '%s': %s", text, exc)

        return found

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
            "featureClass": "P",
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
    def resolve_tag(cls, tag: str, fast_mode: bool = False) -> dict[str, Any] | None:
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

        # 2. Fallback to DBpedia category / synset concept (skipped in fast mode)
        if not fast_mode:
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
        except requests.RequestException as exc:
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


def resolve_manifestation_links(manifestation_id: int, fast_mode: bool = False) -> list[SemanticLink]:
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

    auto_threshold = ConfigService.get_float("LOD_AUTO_APPLY_THRESHOLD", 0.82)
    suggestion_threshold = ConfigService.get_float("LOD_SUGGESTION_THRESHOLD", 0.55)

    pub_year: int | None = None
    if manifestation.publication_date:
        pub_year = manifestation.publication_date.year
    elif manifestation.meta:
        py_val = manifestation.meta.get("publication_year") or manifestation.meta.get("publish_year") or manifestation.meta.get("year")
        if py_val:
            try:
                pub_year = int(str(py_val)[:4])
            except (ValueError, TypeError):
                pass

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
            year=pub_year,
            fast_mode=fast_mode,
        )
        if work_match and work_match["confidence"] >= suggestion_threshold:
            existing = db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "work",
                    SemanticLink.entity_id == work.id,
                    SemanticLink.authority == "dbpedia",
                    SemanticLink.external_uri == work_match["uri"],
                )
            ).scalar_one_or_none()

            if not existing:
                link_status = "accepted" if work_match["confidence"] >= auto_threshold else "suggested"
                link = SemanticLink(
                    entity_type="work",
                    entity_id=work.id,
                    authority="dbpedia",
                    external_uri=work_match["uri"],
                    pref_label=work_match["label"],
                    confidence=work_match["confidence"],
                    match_strategy=work_match["strategy"],
                    attributes=work_match["attributes"],
                    status=link_status,
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
            author_match = DBpediaClient.resolve_person(author_name, fast_mode=fast_mode)
            if author_match and author_match["confidence"] >= suggestion_threshold:
                existing_author = db.session.execute(
                    select(SemanticLink).where(
                        SemanticLink.entity_type == "work",
                        SemanticLink.entity_id == work.id,
                        SemanticLink.authority == "dbpedia",
                        SemanticLink.external_uri == author_match["uri"],
                    )
                ).scalar_one_or_none()

                if not existing_author:
                    author_status = "accepted" if author_match["confidence"] >= auto_threshold else "suggested"
                    author_link = SemanticLink(
                        entity_type="work",
                        entity_id=work.id,
                        authority="dbpedia",
                        external_uri=author_match["uri"],
                        pref_label=author_match["label"],
                        confidence=author_match["confidence"],
                        match_strategy=author_match["strategy"],
                        attributes={**author_match["attributes"], "role": "author"},
                        status=author_status,
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
            wn_match = WordNetMapper.resolve_tag(tag, fast_mode=fast_mode)
            if wn_match and wn_match["confidence"] >= suggestion_threshold:
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
                    wn_status = "accepted" if wn_match["confidence"] >= auto_threshold else "suggested"
                    wn_link = SemanticLink(
                        entity_type="work",
                        entity_id=work.id,
                        authority=authority,
                        external_uri=wn_match["uri"],
                        pref_label=wn_match["label"],
                        confidence=wn_match["confidence"],
                        match_strategy=wn_match["strategy"],
                        attributes=wn_match["attributes"],
                        status=wn_status,
                        verified=False,
                    )
                    db.session.add(wn_link)
                    created_links.append(wn_link)

        # 1d. GeoNames Geographic Subject / Topic Resolutions (FRBR Work Level)
        geo_work_locations: list[dict[str, Any]] = []

        # Extract major cities from title (e.g. "Time Out Copenhagen")
        title_to_scan = (work.title or manifestation.title or "").strip()
        if title_to_scan:
            geo_work_locations.extend(GeoNamesClient.extract_locations_from_text(title_to_scan))

        # Extract from work and manifestation subject places and subjects
        raw_subjects: list[str] = []
        if work.meta:
            for s_field in ("subject_places", "subjects", "tags"):
                s_val = work.meta.get(s_field)
                if isinstance(s_val, list):
                    for item in s_val:
                        if isinstance(item, dict):
                            name_val = item.get("name") or item.get("value") or item.get("label")
                            if name_val:
                                raw_subjects.append(str(name_val))
                        elif isinstance(item, str):
                            raw_subjects.append(item)
                elif isinstance(s_val, str):
                    raw_subjects.append(s_val)

        if manifestation.meta:
            for s_field in ("subject_places", "subjects"):
                s_val = manifestation.meta.get(s_field)
                if isinstance(s_val, list):
                    for item in s_val:
                        if isinstance(item, dict):
                            name_val = item.get("name") or item.get("value") or item.get("label")
                            if name_val:
                                raw_subjects.append(str(name_val))
                        elif isinstance(item, str):
                            raw_subjects.append(item)

        for subj_str in raw_subjects[:5]:
            matched_geo = GeoNamesClient.resolve_location(subj_str)
            if matched_geo:
                geo_work_locations.append(matched_geo)

        for geo_match in geo_work_locations:
            if geo_match.get("confidence", 0.0) < suggestion_threshold:
                continue
            existing_geo_work = db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "work",
                    SemanticLink.entity_id == work.id,
                    SemanticLink.authority == "geonames",
                    SemanticLink.external_uri == geo_match["uri"],
                )
            ).scalar_one_or_none()

            if not existing_geo_work:
                geo_status = "accepted" if geo_match["confidence"] >= auto_threshold else "suggested"
                geo_work_link = SemanticLink(
                    entity_type="work",
                    entity_id=work.id,
                    authority="geonames",
                    external_uri=geo_match["uri"],
                    pref_label=geo_match["label"],
                    confidence=geo_match["confidence"],
                    match_strategy=geo_match["strategy"],
                    attributes={**geo_match["attributes"], "role": "subject_place"},
                    status=geo_status,
                    verified=False,
                )
                db.session.add(geo_work_link)
                created_links.append(geo_work_link)

    # -------------------------------------------------------------------------
    # 2. Manifestation-Level Resolutions (F3)
    # -------------------------------------------------------------------------
    manifestation_places: list[str] = []
    if manifestation.meta:
        for p_field in ("publication_place", "publish_places", "city", "place"):
            p_val = manifestation.meta.get(p_field)
            if isinstance(p_val, list):
                for item in p_val:
                    if isinstance(item, dict):
                        name_val = item.get("name") or item.get("value") or item.get("label")
                        if name_val:
                            manifestation_places.append(str(name_val))
                    elif isinstance(item, str):
                        manifestation_places.append(item)
            elif isinstance(p_val, dict):
                name_val = p_val.get("name") or p_val.get("value") or p_val.get("label")
                if name_val:
                    manifestation_places.append(str(name_val))
            elif isinstance(p_val, str):
                manifestation_places.append(p_val)

    for place_str in manifestation_places[:3]:
        geo_match = GeoNamesClient.resolve_location(place_str)
        if geo_match and geo_match.get("confidence", 0.0) >= suggestion_threshold:
            existing_geo = db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "manifestation",
                    SemanticLink.entity_id == manifestation.id,
                    SemanticLink.authority == "geonames",
                    SemanticLink.external_uri == geo_match["uri"],
                )
            ).scalar_one_or_none()

            if not existing_geo:
                geo_status = "accepted" if geo_match["confidence"] >= auto_threshold else "suggested"
                geo_link = SemanticLink(
                    entity_type="manifestation",
                    entity_id=manifestation.id,
                    authority="geonames",
                    external_uri=geo_match["uri"],
                    pref_label=geo_match["label"],
                    confidence=geo_match["confidence"],
                    match_strategy=geo_match["strategy"],
                    attributes={**geo_match["attributes"], "role": "publication_place"},
                    status=geo_status,
                    verified=False,
                )
                db.session.add(geo_link)
                created_links.append(geo_link)

    # Publisher imprint city (e.g. "Wydawnictwo Literackie, Kraków" or "London : Penguin")
    if manifestation.publisher:
        publisher_cities = GeoNamesClient.extract_locations_from_text(manifestation.publisher)
        if not publisher_cities and ("," in manifestation.publisher or ":" in manifestation.publisher):
            for part in [p.strip() for p in manifestation.publisher.replace(":", ",").split(",") if p.strip()]:
                m_part = GeoNamesClient.resolve_location(part)
                if m_part:
                    publisher_cities.append(m_part)

        for pub_match in publisher_cities[:2]:
            conf = pub_match.get("confidence", 0.90)
            if conf < suggestion_threshold:
                continue
            existing_geo = db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "manifestation",
                    SemanticLink.entity_id == manifestation.id,
                    SemanticLink.authority == "geonames",
                    SemanticLink.external_uri == pub_match["uri"],
                )
            ).scalar_one_or_none()

            if not existing_geo:
                pub_status = "accepted" if conf >= auto_threshold else "suggested"
                geo_link = SemanticLink(
                    entity_type="manifestation",
                    entity_id=manifestation.id,
                    authority="geonames",
                    external_uri=pub_match["uri"],
                    pref_label=pub_match["label"],
                    confidence=conf,
                    match_strategy="publisher_imprint",
                    attributes={**pub_match["attributes"], "role": "publication_place"},
                    status=pub_status,
                    verified=False,
                )
                db.session.add(geo_link)
                created_links.append(geo_link)

    # Fallback: If manifestation has no work, attach title location to manifestation
    if not work and manifestation.title:
        title_cities = GeoNamesClient.extract_locations_from_text(manifestation.title)
        for t_match in title_cities[:2]:
            conf = t_match.get("confidence", 0.85)
            if conf < suggestion_threshold:
                continue
            existing_geo = db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "manifestation",
                    SemanticLink.entity_id == manifestation.id,
                    SemanticLink.authority == "geonames",
                    SemanticLink.external_uri == t_match["uri"],
                )
            ).scalar_one_or_none()

            if not existing_geo:
                t_status = "accepted" if conf >= auto_threshold else "suggested"
                geo_link = SemanticLink(
                    entity_type="manifestation",
                    entity_id=manifestation.id,
                    authority="geonames",
                    external_uri=t_match["uri"],
                    pref_label=t_match["label"],
                    confidence=conf,
                    match_strategy=t_match["strategy"],
                    attributes={**t_match["attributes"], "role": "subject_place"},
                    status=t_status,
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

    all_links = manifestation.get_semantic_links(include_work=True, status=None)
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
