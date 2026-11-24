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
"""Cross-media FRBR Work linking and reconciliation service.

Discovers candidate semantic relationships (e.g., book <-> film adaptation,
soundtrack, novelization, video-game adaptation) across distinct FRBR Works
whose Expressions belong to divergent media categories.

Confirmed relationships are stored in :class:`~app.db.core.WorkRelation` and
never trigger :mod:`app.core.frbr_merge`, preserving separate Works,
Expressions, Manifestations, and Items across media types.
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

import requests
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY, FORMAT_TO_CATEGORY, get_format_categories
from app.db import db
from app.db.contributions import WorkSeriesMembership
from app.db.core import (
    WORK_RELATION_TYPES,
    Expression,
    SemanticLink,
    Work,
    WorkLinkCandidate,
    WorkRelation,
)
from app.utils.vision import validate_ollama_url

logger = logging.getLogger(__name__)

WORK_LINK_CANDIDATE_STATUS_PENDING: str = "pending"
WORK_LINK_CANDIDATE_STATUS_ACCEPTED: str = "accepted"
WORK_LINK_CANDIDATE_STATUS_DISMISSED: str = "dismissed"
WORK_LINK_RESOLUTION_HEURISTIC: str = "heuristic"
WORK_LINK_RESOLUTION_LLM: str = "llm"
WORK_RELATION_IS_ADAPTATION_OF: str = "is_adaptation_of"

ENGINE_HEURISTIC: str = WORK_LINK_RESOLUTION_HEURISTIC
ENGINE_LLAMA: str = "llama"
DEFAULT_ENGINE: str = ENGINE_HEURISTIC
VALID_ENGINES: tuple[str, ...] = (ENGINE_HEURISTIC, ENGINE_LLAMA)

DEFAULT_THRESHOLD: float = 0.70
SCAN_PAGE_SIZE: int = 200
MAX_BLOCK_SIZE: int = 40
MAX_LLM_EVALUATIONS_PER_RUN: int = 100

_LEADING_ARTICLES_RE = re.compile(r"^(?:the|a|an|ten|ta|to)\s+", re.IGNORECASE)
_SUFFIX_NOISE_RE = re.compile(
    r"\s*[\(\[](?:film|movie|book|novel|soundtrack|ost|score|game|video game|board game|tv|series|dvd|blu-ray|\d{4})[\)\]]\s*",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_STOPWORDS: frozenset[str] = frozenset({"the", "a", "an", "and", "of", "in", "on", "to", "for", "with", "ten", "ta", "i", "w", "z"})

# Media category precedence for inferring derived -> source direction when
# publication years are unavailable (higher rank typically adapts lower rank).
_MEDIA_DERIVATION_RANK: dict[str, int] = {
    "book": 1,
    "comic": 2,
    "manga": 2,
    "magazine": 2,
    "board_game": 3,
    "movie": 4,
    "tv_show": 4,
    "video_game": 5,
    "music": 6,
    "audio": 6,
}


class WorkLinkingError(RuntimeError):
    """Base error for cross-media Work linking operations."""


class WorkLinkPrerequisiteError(WorkLinkingError):
    """Raised when an optional LLM engine prerequisite (Ollama) is unavailable."""


class WorkLinkCycleError(WorkLinkingError):
    """Raised when a WorkRelation would create a self-link or directed cycle."""


class WorkLinkNotFoundError(WorkLinkingError):
    """Raised when a target Work, WorkLinkCandidate, or WorkRelation does not exist."""


@dataclass
class CrossMediaScanReport:
    """Summary counters produced by a cross-media reconciliation scan."""

    works_scanned: int = 0
    candidate_pairs: int = 0
    llm_evaluations: int = 0
    llm_failures: int = 0
    below_threshold: int = 0
    already_known: int = 0
    created: int = 0
    would_create: int = 0
    dry_run: bool = True
    engine: str = DEFAULT_ENGINE


@dataclass
class _WorkProfile:
    """Lightweight in-memory representation of a Work for blocking and scoring."""

    work_id: int
    title: str
    norm_title: str
    stem_title: str
    tokens: frozenset[str]
    categories: frozenset[str]
    contributor_ids: frozenset[int]
    series_ids: frozenset[int]
    lod_uris: frozenset[str]
    year: int | None


def normalize_work_title(title: str | None) -> str:
    """Normalize a Work title for cross-media blocking and similarity scoring."""
    if not title:
        return ""
    cleaned = _SUFFIX_NOISE_RE.sub(" ", str(title))
    nfkd = unicodedata.normalize("NFKD", cleaned)
    ascii_folded = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    lowered = _PUNCT_RE.sub(" ", ascii_folded.lower())
    collapsed = " ".join(lowered.split())
    return _LEADING_ARTICLES_RE.sub("", collapsed).strip()


def _extract_stem_title(title: str | None) -> str:
    """Extract normalized prefix before subtitle separators (':' or ' - ')."""
    if not title:
        return ""
    for sep in (":", " - ", " — ", " – "):
        if sep in title:
            prefix = title.split(sep, 1)[0].strip()
            norm_prefix = normalize_work_title(prefix)
            if len(norm_prefix) >= 4:
                return norm_prefix
    return normalize_work_title(title)


def _extract_categories(expressions: list[Expression]) -> frozenset[str]:
    """Resolve taxonomy media categories for a Work from its Expressions."""
    cats: set[str] = set()
    for expr in expressions:
        raw_ct = (expr.content_type or "").strip().lower()
        if not raw_ct:
            continue
        mapped = get_format_categories(raw_ct)
        if mapped:
            cats.update(mapped)
        elif raw_ct in FORMAT_TO_CATEGORY:
            cats.add(FORMAT_TO_CATEGORY[raw_ct])
        elif raw_ct in FORMAT_ALIAS_TO_CATEGORY:
            cats.add(FORMAT_ALIAS_TO_CATEGORY[raw_ct])
        else:
            cats.add(raw_ct)
    return frozenset(cats)


def _extract_year(work: Work) -> int | None:
    """Best-effort integer publication/release year from Work.meta."""
    meta = work.meta if isinstance(work.meta, dict) else {}
    for key in ("publication_year", "release_year", "year", "first_publish_year"):
        val = meta.get(key)
        if val is not None:
            try:
                year = int(str(val)[:4])
                if 1000 <= year <= 2200:
                    return year
            except (TypeError, ValueError):
                continue
    return None


def _build_blocking_keys(profile: _WorkProfile) -> set[str]:
    """Generate deterministic blocking keys for Stage 1 pair generation."""
    keys: set[str] = set()
    if profile.norm_title:
        keys.add(f"full:{profile.norm_title}")
    if profile.stem_title:
        keys.add(f"stem:{profile.stem_title}")
    ordered_tokens = [t for t in profile.norm_title.split() if t and t not in _STOPWORDS]
    if len(ordered_tokens) >= 2:
        keys.add(f"pfx2:{ordered_tokens[0]}_{ordered_tokens[1]}")
    for uri in profile.lod_uris:
        keys.add(f"lod:{uri}")
    return keys


def _score_pair(a: _WorkProfile, b: _WorkProfile) -> float:
    """Compute heuristic cross-media link confidence in [0.0, 1.0].

    Disjoint creators (e.g., book author vs. film director) never reduce score.
    """
    if not a.norm_title or not b.norm_title:
        return 0.0

    seq_ratio = SequenceMatcher(None, a.norm_title, b.norm_title).ratio()
    stem_ratio = SequenceMatcher(None, a.stem_title, b.stem_title).ratio() if a.stem_title and b.stem_title else 0.0

    prefix_score = 0.0
    shorter, longer = (a.norm_title, b.norm_title) if len(a.norm_title) <= len(b.norm_title) else (b.norm_title, a.norm_title)
    if len(shorter) >= 5 and (longer.startswith(shorter + " ") or longer.startswith(shorter + ":") or shorter == longer):
        prefix_score = 0.90

    stem_match_score = 0.88 if a.stem_title and b.stem_title and a.stem_title == b.stem_title else 0.0

    union_tokens = a.tokens | b.tokens
    jaccard = (len(a.tokens & b.tokens) / len(union_tokens)) if union_tokens else 0.0
    # Shared prefix token boost for regional adaptations (e.g., Philosopher's vs Sorcerer's Stone)
    token_score = jaccard * 0.95 if len(a.tokens & b.tokens) >= 3 else jaccard * 0.80

    base = max(seq_ratio, stem_ratio * 0.92, prefix_score, stem_match_score, token_score)

    bonus = 0.0
    if a.contributor_ids & b.contributor_ids:
        bonus += 0.10
    if a.series_ids & b.series_ids:
        bonus += 0.08
    if a.lod_uris & b.lod_uris:
        bonus += 0.15

    return round(min(1.0, base + bonus), 4)


def _infer_direction_and_relation(a: _WorkProfile, b: _WorkProfile) -> tuple[int, int, str]:
    """Infer (source_derived_work_id, target_original_work_id, relation_type)."""
    rank_a = min((_MEDIA_DERIVATION_RANK.get(cat, 3) for cat in a.categories), default=3)
    rank_b = min((_MEDIA_DERIVATION_RANK.get(cat, 3) for cat in b.categories), default=3)

    if rank_a > rank_b:
        source_id, target_id = a.work_id, b.work_id
    elif rank_b > rank_a:
        source_id, target_id = b.work_id, a.work_id
    elif a.year is not None and b.year is not None and a.year != b.year:
        source_id, target_id = (a.work_id, b.work_id) if a.year > b.year else (b.work_id, a.work_id)
    else:
        source_id, target_id = (max(a.work_id, b.work_id), min(a.work_id, b.work_id))

    return source_id, target_id, WORK_RELATION_IS_ADAPTATION_OF


def _resolve_ollama_config() -> tuple[str, str]:
    """Resolve and SSRF-validate Ollama URL and model name for ENGINE_LLAMA."""
    raw_url = os.environ.get("OLLAMA_URL", "http://localhost:11434").strip()
    if not raw_url:
        raw_url = "http://localhost:11434"
    try:
        safe_url = validate_ollama_url(raw_url)
    except ValueError as exc:
        raise WorkLinkPrerequisiteError(str(exc)) from exc
    model = os.environ.get("OLLAMA_DEDUPE_MODEL", "llama3.1").strip() or "llama3.1"
    return safe_url, model


def _check_ollama_health(base_url: str, model: str) -> None:
    """Verify local Ollama daemon reachability before running LLM evaluations."""
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        payload = resp.json() if resp.content else {}
    except (requests.RequestException, ValueError) as exc:
        raise WorkLinkPrerequisiteError(f"Ollama unavailable at {base_url}: {exc}") from exc

    models = payload.get("models") or []
    names = {str(m.get("name", "")).split(":", 1)[0] for m in models if isinstance(m, dict)}
    requested_base = model.split(":", 1)[0]
    if names and requested_base not in names and model not in {str(m.get("name", "")) for m in models if isinstance(m, dict)}:
        raise WorkLinkPrerequisiteError(f"Ollama model '{model}' is not pulled at {base_url}")


def _adjudicate_with_ollama(
    base_url: str,
    model: str,
    source_profile: _WorkProfile,
    target_profile: _WorkProfile,
    heuristic_score: float,
) -> tuple[bool, str, float, str] | None:
    """Ask local Ollama to adjudicate a cross-media Work pair."""
    prompt = (
        "You are an FRBR cataloger. Decide if these two Works in different media "
        "have a derivative/adaptation relationship.\n"
        f"Work A (source candidate): title={source_profile.title!r}, media={sorted(source_profile.categories)}\n"
        f"Work B (target candidate): title={target_profile.title!r}, media={sorted(target_profile.categories)}\n"
        f"Heuristic similarity={heuristic_score:.2f}. Allowed relation_type values: {list(WORK_RELATION_TYPES)}.\n"
        'Respond strictly as JSON: {"is_related": bool, "relation_type": str, "confidence": float, "reasoning": str}.'
    )
    try:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_response = data.get("response", "")
        parsed = json.loads(raw_response) if isinstance(raw_response, str) else raw_response
        if not isinstance(parsed, dict):
            return None
        is_related = bool(parsed.get("is_related", False))
        rel_type = str(parsed.get("relation_type") or WORK_RELATION_IS_ADAPTATION_OF)
        if rel_type not in WORK_RELATION_TYPES:
            rel_type = WORK_RELATION_IS_ADAPTATION_OF
        confidence = max(0.0, min(1.0, float(parsed.get("confidence", heuristic_score))))
        reasoning = str(parsed.get("reasoning") or "").strip()[:1000]
        return is_related, rel_type, confidence, reasoning
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning("Ollama cross-media evaluation failed for (%s, %s): %s", source_profile.work_id, target_profile.work_id, exc)
        return None


def _load_work_profiles(limit: int | None = None) -> list[_WorkProfile]:
    """Stream Works via bounded keyset pagination and build lightweight profiles."""
    profiles: list[_WorkProfile] = []
    last_id = 0

    while True:
        batch_limit = SCAN_PAGE_SIZE
        if limit is not None:
            remaining = limit - len(profiles)
            if remaining <= 0:
                break
            batch_limit = min(batch_limit, remaining)

        works = (
            db.session.execute(
                select(Work)
                .options(
                    selectinload(Work.expressions),
                    selectinload(Work.contributions),
                )
                .where(Work.id > last_id)
                .order_by(Work.id.asc())
                .limit(batch_limit)
            )
            .scalars()
            .all()
        )
        if not works:
            break

        work_ids = [w.id for w in works]
        series_map: dict[int, set[int]] = defaultdict(set)
        for membership in (
            db.session.execute(select(WorkSeriesMembership).where(WorkSeriesMembership.work_id.in_(work_ids))).scalars().all()
        ):
            series_map[membership.work_id].add(membership.series_work_id)

        lod_map: dict[int, set[str]] = defaultdict(set)
        for link in (
            db.session.execute(
                select(SemanticLink).where(
                    SemanticLink.entity_type == "work",
                    SemanticLink.entity_id.in_(work_ids),
                    SemanticLink.status == "accepted",
                )
            )
            .scalars()
            .all()
        ):
            if link.external_uri:
                lod_map[link.entity_id].add(link.external_uri.strip())

        for work in works:
            last_id = work.id
            categories = _extract_categories(list(work.expressions or []))
            if not categories:
                continue
            norm_title = normalize_work_title(work.title)
            stem_title = _extract_stem_title(work.title)
            tokens = frozenset(t for t in norm_title.split() if t and t not in _STOPWORDS)
            contrib_ids = frozenset(c.contributor_id for c in (work.contributions or []) if c.contributor_id is not None)
            profiles.append(
                _WorkProfile(
                    work_id=work.id,
                    title=work.title,
                    norm_title=norm_title,
                    stem_title=stem_title,
                    tokens=tokens,
                    categories=categories,
                    contributor_ids=contrib_ids,
                    series_ids=frozenset(series_map.get(work.id, set())),
                    lod_uris=frozenset(lod_map.get(work.id, set())),
                    year=_extract_year(work),
                )
            )

        if len(works) < batch_limit:
            break

    return profiles


def scan_cross_media_links(
    *,
    engine: str = DEFAULT_ENGINE,
    threshold: float = DEFAULT_THRESHOLD,
    limit: int | None = None,
    dry_run: bool = True,
    skip_health_check: bool = False,
) -> CrossMediaScanReport:
    """Scan the catalog for cross-media Work link candidates.

    Uses bounded keyset scanning, title/stem/LOD blocking, and optional local
    Ollama adjudication. Persists only new ``pending`` candidates when
    ``dry_run=False``.
    """
    if engine not in VALID_ENGINES:
        raise WorkLinkingError(f"Unsupported engine '{engine}'. Expected one of {VALID_ENGINES}.")
    if not 0.0 <= threshold <= 1.0:
        raise WorkLinkingError("Threshold must be between 0.0 and 1.0.")

    ollama_url = ""
    ollama_model = ""
    if engine == ENGINE_LLAMA:
        ollama_url, ollama_model = _resolve_ollama_config()
        if not skip_health_check:
            _check_ollama_health(ollama_url, ollama_model)

    profiles = _load_work_profiles(limit=limit)
    report = CrossMediaScanReport(works_scanned=len(profiles), dry_run=dry_run, engine=engine)
    if len(profiles) < 2:
        return report

    profile_by_id = {p.work_id: p for p in profiles}
    buckets: dict[str, list[int]] = defaultdict(list)
    for prof in profiles:
        for key in _build_blocking_keys(prof):
            buckets[key].append(prof.work_id)

    candidate_pair_ids: set[tuple[int, int]] = set()
    for work_ids in buckets.values():
        if len(work_ids) < 2 or len(work_ids) > MAX_BLOCK_SIZE:
            continue
        sorted_ids = sorted(set(work_ids))
        for i, wid_a in enumerate(sorted_ids):
            prof_a = profile_by_id[wid_a]
            for wid_b in sorted_ids[i + 1 :]:
                prof_b = profile_by_id[wid_b]
                if not prof_a.categories.isdisjoint(prof_b.categories):
                    continue
                candidate_pair_ids.add((wid_a, wid_b))

    report.candidate_pairs = len(candidate_pair_ids)
    if not candidate_pair_ids:
        return report

    # Preload existing confirmed WorkRelations and WorkLinkCandidates for idempotency.
    existing_relations: set[tuple[int, int]] = set()
    for rel in db.session.execute(select(WorkRelation.source_work_id, WorkRelation.target_work_id)).all():
        existing_relations.add((min(rel[0], rel[1]), max(rel[0], rel[1])))

    existing_candidates: set[tuple[int, int]] = set()
    for cand in db.session.execute(select(WorkLinkCandidate.source_work_id, WorkLinkCandidate.target_work_id)).all():
        existing_candidates.add((min(cand[0], cand[1]), max(cand[0], cand[1])))

    for wid_a, wid_b in sorted(candidate_pair_ids):
        canonical_pair = (min(wid_a, wid_b), max(wid_a, wid_b))
        if canonical_pair in existing_relations or canonical_pair in existing_candidates:
            report.already_known += 1
            continue

        prof_a = profile_by_id[wid_a]
        prof_b = profile_by_id[wid_b]
        score = _score_pair(prof_a, prof_b)
        if score < threshold:
            report.below_threshold += 1
            continue

        src_id, tgt_id, rel_type = _infer_direction_and_relation(prof_a, prof_b)
        src_prof = profile_by_id[src_id]
        tgt_prof = profile_by_id[tgt_id]
        res_source = ENGINE_HEURISTIC
        reasoning: str | None = None

        if engine == ENGINE_LLAMA and report.llm_evaluations < MAX_LLM_EVALUATIONS_PER_RUN:
            report.llm_evaluations += 1
            verdict = _adjudicate_with_ollama(ollama_url, ollama_model, src_prof, tgt_prof, score)
            if verdict is None:
                report.llm_failures += 1
                continue
            is_related, llm_rel_type, llm_conf, llm_reason = verdict
            if not is_related or llm_conf < threshold:
                report.below_threshold += 1
                continue
            rel_type = llm_rel_type
            score = llm_conf
            reasoning = llm_reason
            res_source = WORK_LINK_RESOLUTION_LLM

        if dry_run:
            report.would_create += 1
            continue

        db.session.add(
            WorkLinkCandidate(
                source_work_id=src_id,
                target_work_id=tgt_id,
                proposed_relation_type=rel_type,
                confidence=score,
                resolution_source=res_source,
                llm_reasoning=reasoning,
                status=WORK_LINK_CANDIDATE_STATUS_PENDING,
            )
        )
        existing_candidates.add(canonical_pair)
        report.created += 1

    if not dry_run and report.created > 0:
        try:
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            raise WorkLinkingError(f"Failed to persist cross-media candidates: {exc}") from exc

    return report


def _would_create_cycle(source_work_id: int, target_work_id: int) -> bool:
    """Return True if adding edge source -> target would create a self-link or cycle."""
    if source_work_id == target_work_id:
        return True

    visited: set[int] = {target_work_id}
    queue: deque[int] = deque([target_work_id])
    while queue:
        current = queue.popleft()
        next_targets = db.session.execute(select(WorkRelation.target_work_id).where(WorkRelation.source_work_id == current)).scalars().all()
        for nxt in next_targets:
            if nxt == source_work_id:
                return True
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return False


def create_work_relation(
    *,
    source_work_id: int,
    target_work_id: int,
    relation_type: str,
    created_by_id: UUID | None = None,
    notes: str | None = None,
) -> WorkRelation:
    """Create a confirmed cross-media WorkRelation with self-link and DAG cycle guards."""
    if relation_type not in WORK_RELATION_TYPES:
        raise WorkLinkingError(f"Invalid relation_type '{relation_type}'.")
    if source_work_id == target_work_id:
        raise WorkLinkCycleError("A Work cannot be linked to itself.")

    src_work = db.session.get(Work, source_work_id)
    tgt_work = db.session.get(Work, target_work_id)
    if src_work is None or tgt_work is None:
        raise WorkLinkNotFoundError("Source or target Work not found.")

    existing = db.session.execute(
        select(WorkRelation).where(
            WorkRelation.source_work_id == source_work_id,
            WorkRelation.target_work_id == target_work_id,
            WorkRelation.relation_type == relation_type,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    if _would_create_cycle(source_work_id, target_work_id):
        raise WorkLinkCycleError("Linking these Works would introduce a cycle in the derivation graph.")

    relation = WorkRelation(
        source_work_id=source_work_id,
        target_work_id=target_work_id,
        relation_type=relation_type,
        notes=notes,
        created_by_id=created_by_id,
    )
    db.session.add(relation)
    db.session.commit()
    return relation


def accept_candidate(
    candidate_id: int,
    *,
    resolved_by_id: UUID | None = None,
    relation_type: str | None = None,
    source_work_id: int | None = None,
    target_work_id: int | None = None,
    notes: str | None = None,
) -> tuple[WorkLinkCandidate, WorkRelation]:
    """Confirm a pending WorkLinkCandidate into a WorkRelation (never merges)."""
    candidate = db.session.get(WorkLinkCandidate, candidate_id)
    if candidate is None:
        raise WorkLinkNotFoundError(f"WorkLinkCandidate {candidate_id} not found.")

    src_id = source_work_id if source_work_id is not None else candidate.source_work_id
    tgt_id = target_work_id if target_work_id is not None else candidate.target_work_id
    rel_type = relation_type or candidate.proposed_relation_type

    relation = create_work_relation(
        source_work_id=src_id,
        target_work_id=tgt_id,
        relation_type=rel_type,
        created_by_id=resolved_by_id,
        notes=notes,
    )
    candidate.status = WORK_LINK_CANDIDATE_STATUS_ACCEPTED
    candidate.resolved_at = datetime.now(UTC)
    candidate.resolved_by_id = resolved_by_id
    db.session.commit()
    return candidate, relation


def dismiss_candidate(candidate_id: int, *, resolved_by_id: UUID | None = None) -> WorkLinkCandidate:
    """Dismiss a WorkLinkCandidate so subsequent scans do not re-queue it."""
    candidate = db.session.get(WorkLinkCandidate, candidate_id)
    if candidate is None:
        raise WorkLinkNotFoundError(f"WorkLinkCandidate {candidate_id} not found.")

    candidate.status = WORK_LINK_CANDIDATE_STATUS_DISMISSED
    candidate.resolved_at = datetime.now(UTC)
    candidate.resolved_by_id = resolved_by_id
    db.session.commit()
    return candidate


def delete_work_relation(relation_id: int) -> None:
    """Delete a confirmed WorkRelation without touching underlying Works."""
    relation = db.session.get(WorkRelation, relation_id)
    if relation is None:
        raise WorkLinkNotFoundError(f"WorkRelation {relation_id} not found.")
    db.session.delete(relation)
    db.session.commit()


def serialize_candidate(candidate: WorkLinkCandidate) -> dict[str, Any]:
    """Serialize a WorkLinkCandidate with source and target Work summaries."""
    src = candidate.source_work
    tgt = candidate.target_work
    return {
        "id": candidate.id,
        "source_work_id": candidate.source_work_id,
        "target_work_id": candidate.target_work_id,
        "source_work_title": src.title if src else None,
        "target_work_title": tgt.title if tgt else None,
        "source_categories": sorted(_extract_categories(list(src.expressions or []))) if src else [],
        "target_categories": sorted(_extract_categories(list(tgt.expressions or []))) if tgt else [],
        "proposed_relation_type": candidate.proposed_relation_type,
        "confidence": candidate.confidence,
        "resolution_source": candidate.resolution_source,
        "llm_reasoning": candidate.llm_reasoning,
        "status": candidate.status,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        "resolved_at": candidate.resolved_at.isoformat() if candidate.resolved_at else None,
    }


def serialize_relation(relation: WorkRelation) -> dict[str, Any]:
    """Serialize a confirmed WorkRelation with source and target Work summaries."""
    src = relation.source_work
    tgt = relation.target_work
    return {
        "id": relation.id,
        "source_work_id": relation.source_work_id,
        "target_work_id": relation.target_work_id,
        "source_work_title": src.title if src else None,
        "target_work_title": tgt.title if tgt else None,
        "source_categories": sorted(_extract_categories(list(src.expressions or []))) if src else [],
        "target_categories": sorted(_extract_categories(list(tgt.expressions or []))) if tgt else [],
        "relation_type": relation.relation_type,
        "notes": relation.notes,
        "created_at": relation.created_at.isoformat() if relation.created_at else None,
        "updated_at": relation.updated_at.isoformat() if relation.updated_at else None,
    }


def list_work_link_candidates(
    *,
    status: str | None = WORK_LINK_CANDIDATE_STATUS_PENDING,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[WorkLinkCandidate], int]:
    """Return SQL-paginated WorkLinkCandidate rows and total count."""
    from sqlalchemy import func

    base_stmt = select(WorkLinkCandidate).options(
        selectinload(WorkLinkCandidate.source_work).selectinload(Work.expressions),
        selectinload(WorkLinkCandidate.target_work).selectinload(Work.expressions),
    )
    count_stmt = select(func.count(WorkLinkCandidate.id))  # pylint: disable=not-callable
    if status:
        base_stmt = base_stmt.where(WorkLinkCandidate.status == status)
        count_stmt = count_stmt.where(WorkLinkCandidate.status == status)

    total = int(db.session.execute(count_stmt).scalar_one() or 0)
    rows = (
        db.session.execute(base_stmt.order_by(WorkLinkCandidate.confidence.desc(), WorkLinkCandidate.id.asc()).limit(limit).offset(offset))
        .scalars()
        .all()
    )
    return list(rows), total


def list_work_relations(
    *,
    work_id: int | None = None,
    relation_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[WorkRelation], int]:
    """Return SQL-paginated confirmed WorkRelation rows and total count."""
    from sqlalchemy import func

    base_stmt = select(WorkRelation).options(
        selectinload(WorkRelation.source_work).selectinload(Work.expressions),
        selectinload(WorkRelation.target_work).selectinload(Work.expressions),
    )
    count_stmt = select(func.count(WorkRelation.id))  # pylint: disable=not-callable
    if work_id is not None:
        cond = or_(WorkRelation.source_work_id == work_id, WorkRelation.target_work_id == work_id)
        base_stmt = base_stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if relation_type:
        base_stmt = base_stmt.where(WorkRelation.relation_type == relation_type)
        count_stmt = count_stmt.where(WorkRelation.relation_type == relation_type)

    total = int(db.session.execute(count_stmt).scalar_one() or 0)
    rows = db.session.execute(base_stmt.order_by(WorkRelation.id.desc()).limit(limit).offset(offset)).scalars().all()
    return list(rows), total
