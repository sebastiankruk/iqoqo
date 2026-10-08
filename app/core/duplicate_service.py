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
"""FRBR duplicate detection and entity resolution service.

Detection runs in two stages, mirroring the cost profile of a local-first
deployment where inference happens on the owner's own hardware:

1. **Heuristic screening** blocks the catalog on cheap, deterministic keys
   (normalized title, sort title, creator overlap, ISBN) and prunes the pair set
   before any inference happens.  Without this stage a library of *N* entities
   would need ``O(N^2)`` LLM round-trips.
2. **LLM verification** asks a local Ollama model to judge semantic equivalence
   of each surviving pair and to explain its verdict.

Only pairs that clear the confidence threshold are persisted to
:class:`~app.db.core.DuplicateCandidate` for administrative review.  Merging is
always a separate, explicitly confirmed administrative action: this module
never merges on its own.

Every merge is transactional and FRBR-preserving — child Expressions are
re-parented to the surviving Work, child Items to the surviving Manifestation,
and every other table referencing the discarded entity is consolidated onto the
survivor so that no user data is silently cascade-deleted.  ISBN identifiers are
consolidated strictly on the Manifestation (FRBRoo F3) and are never promoted to
a parent Work or Expression.
"""

from __future__ import annotations

import json
import logging
import os
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

import requests
from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core import frbr_merge
from app.db import db
from app.db.auth import User
from app.db.contributions import ExpressionContribution, WorkContribution
from app.db.core import (
    DUPLICATE_ENTITY_TIERS,
    DUPLICATE_RESOLUTION_HEURISTIC,
    DUPLICATE_RESOLUTION_LLAMA,
    DUPLICATE_RESOLUTION_SOURCES,
    DUPLICATE_STATUS_DISMISSED,
    DUPLICATE_STATUS_MERGED,
    DUPLICATE_STATUS_PENDING,
    DuplicateCandidate,
    EntityAuditLog,
    Expression,
    Manifestation,
    Work,
)

logger = logging.getLogger(__name__)

#: Default minimum LLM confidence required to queue a candidate for review.
DEFAULT_THRESHOLD: float = 0.80

#: Minimum normalized-title similarity for a heuristically screened pair to
#: reach the LLM.  Deliberately permissive — the LLM is the arbiter, this stage
#: only removes pairs that cannot plausibly be duplicates.
TITLE_SIMILARITY_FLOOR: float = 0.72

#: Minimum sort-title similarity when creator overlap corroborates a
#: below-floor title match (e.g. the same book with a translated subtitle).
SORT_TITLE_FLOOR_WITH_CREATOR_OVERLAP: float = 0.60

#: Keyset page size for catalog scanning.  Detection never materializes an
#: unbounded result set (see SQL pagination rule).
SCAN_PAGE_SIZE: int = 200

#: Hard ceiling on the number of heuristic candidate pairs handed to the LLM in
#: one run, so a pathological catalog cannot start an unbounded inference job.
MAX_LLM_EVALUATIONS_PER_RUN: int = 200

#: Keyset page size for the administrative candidate queue.
QUEUE_PAGE_SIZE_LIMIT: int = 100

#: Detection engines.  ``heuristic`` resolves candidates deterministically and
#: never contacts a model; ``llama`` additionally adjudicates the grey zone the
#: classifier cannot decide.  The default is ``heuristic`` so a scan needs no
#: inference service, which matters for container deployments without a GPU.
ENGINE_HEURISTIC: str = "heuristic"
ENGINE_LLAMA: str = "llama"
DETECTION_ENGINES: tuple[str, ...] = (ENGINE_HEURISTIC, ENGINE_LLAMA)
DEFAULT_ENGINE: str = ENGINE_HEURISTIC

#: Outcomes of the deterministic pre-inference classifier.
CLASSIFICATION_AUTO_ACCEPT: str = "auto_accept"
CLASSIFICATION_AUTO_REJECT: str = "auto_reject"
CLASSIFICATION_NEEDS_LLM: str = "needs_llm"

#: Manifestation attributes that identify a specific printed edition.  A shared
#: value means the two records describe the same physical edition, so the pair
#: needs no confidence threshold at all.  Note that ``isbn13`` is uniquely
#: constrained, so in practice ``ean``/``upc``/``barcode`` are the columns that
#: can actually collide.
CONCLUSIVE_EDITION_IDENTIFIERS: tuple[str, ...] = ("isbn13", "ean", "upc", "barcode")

DEFAULT_OLLAMA_MODEL: str = "llama3:latest"
OLLAMA_TIMEOUT_SECONDS: int = 15
OLLAMA_HEALTH_TIMEOUT_SECONDS: int = 5
#: Leading articles stripped during title normalization, in several languages
#: because catalog titles are not reliably English.
_LEADING_ARTICLES: frozenset[str] = frozenset(
    {
        # English
        "the",
        "a",
        "an",
        # Polish
        "ten",
        "ta",
        "to",
        "ci",
        "ze",
        # German
        "der",
        "die",
        "das",
        # French / Italian / Spanish / Portuguese
        "le",
        "la",
        "les",
        "un",
        "une",
        "il",
        "lo",
        "gli",
        "el",
        "los",
        "las",
        "una",
    }
)

TIER_WORK: str = "work"
TIER_EXPRESSION: str = "expression"
TIER_MANIFESTATION: str = "manifestation"
TIER_ALL: str = "all"

_DETECTION_TIERS: tuple[str, ...] = (*DUPLICATE_ENTITY_TIERS, TIER_ALL)


class DuplicateServiceError(RuntimeError):
    """Raised when a duplicate operation cannot be completed."""


class DuplicateEvaluationError(DuplicateServiceError):
    """Raised when the local LLM could not produce a usable verdict."""


# ---------------------------------------------------------------------------
# Normalization and similarity
# ---------------------------------------------------------------------------


def normalize_title(value: str | None) -> str:
    """Return a comparable, language-agnostic form of a catalog title.

    Strips accents, drops leading articles, lowercases, and reduces all
    punctuation and whitespace to single spaces.  Empty input yields an empty
    string so callers can compare safely.

    Args:
        value: Raw title, sort title, or label text.

    Returns:
        Normalized comparison form of the title.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    tokens = [tok for tok in "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in stripped.lower()).split() if tok]
    while tokens and tokens[0] in _LEADING_ARTICLES:
        tokens.pop(0)
    return " ".join(tokens)


def normalize_creator(value: Any) -> str:
    """Return a comparable form of a single creator name.

    Surname particles are kept because dropping them would make distinct
    creators collide.  Given/family order is normalized to a plain sorted token
    set so ``"Tolkien, J. R. R."`` matches ``"J.R.R. Tolkien"``.

    Args:
        value: Creator name in any of the shapes stored in ``Work.meta``.

    Returns:
        Space-joined, sorted token form of the name, or an empty string.
    """
    normalized = normalize_title(value)
    if not normalized:
        return ""
    return " ".join(sorted(normalized.split()))


def _creator_names(raw: Any) -> list[str]:
    """Extract creator names from the several shapes stored in ``meta``.

    ``Work.meta["authors"]`` is a list in practice but single strings and
    comma-separated values appear from manual entry and legacy imports.

    Args:
        raw: Value read from a ``meta`` JSON column.

    Returns:
        Flat list of non-empty creator name strings.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(raw, (list, tuple)):
        names: list[str] = []
        for entry in raw:
            if isinstance(entry, str) and entry.strip():
                names.append(entry.strip())
            elif isinstance(entry, dict):
                for key in ("name", "author", "creator", "Artist"):
                    value = entry.get(key)
                    if isinstance(value, str) and value.strip():
                        names.append(value.strip())
                        break
        return names
    return []


def work_creators(work: Work) -> set[str]:
    """Return the normalized creator set recorded on a Work.

    Args:
        work: Work whose creators should be collected.

    Returns:
        Set of normalized creator names from ``Work.meta`` authors.
    """
    meta = work.meta if isinstance(work.meta, dict) else {}
    return {normalized for normalized in (normalize_creator(name) for name in _creator_names(meta.get("authors"))) if normalized}


def contribution_creators(contributions: list[Any]) -> set[str]:
    """Return the normalized creator set from contribution rows.

    Args:
        contributions: :class:`WorkContribution` or
            :class:`ManifestationContribution` rows.

    Returns:
        Set of normalized contributor display names.
    """
    return {
        normalized
        for normalized in (normalize_creator(getattr(c, "contributor", None) and c.contributor.name) for c in contributions)
        if normalized
    }


def _expression_creators(expression: Expression) -> set[str]:
    """Return the normalized creator set reachable from an Expression.

    Prefers the parent Work's creators and includes expression-level performance
    contributions (FRBRoo: performers belong to Expression).

    Args:
        expression: Expression to inspect.

    Returns:
        Set of normalized creator names.
    """
    creators: set[str] = set()
    work = expression.work
    if work is not None:
        creators.update(work_creators(work))
    if hasattr(expression, "contributions") and expression.contributions:
        creators.update(contribution_creators(list(expression.contributions)))
    return creators


def title_similarity(left: str | None, right: str | None) -> float:
    """Return a 0.0-1.0 similarity ratio between two titles.

    Uses :class:`difflib.SequenceMatcher` over normalized forms, which is
    deterministic, dependency-free, and adequate for the short strings used in
    bibliographic titles.

    Args:
        left: First title.
        right: Second title.

    Returns:
        Similarity ratio; ``0.0`` when either title normalizes to empty.
    """
    normalized_left = normalize_title(left)
    normalized_right = normalize_title(right)
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


# ---------------------------------------------------------------------------
# Entity descriptions (shared by the LLM prompt and the review UI)
# ---------------------------------------------------------------------------


def describe_work(work: Work) -> dict[str, Any]:
    """Summarize a Work for LLM prompts and review-queue rendering.

    Args:
        work: Work to describe.

    Returns:
        JSON-serializable summary including creator and child-collection sizes.
    """
    meta = work.meta if isinstance(work.meta, dict) else {}
    # ``expressions`` is a plain list relationship (lazy=True), so the child
    # count comes from the eagerly loaded collection rather than a query.
    expression_count = len(work.expressions)
    creator_names = sorted(work_creators(work))
    if not creator_names:
        creator_names = sorted(contribution_creators(list(work.contributions)))
    return {
        "tier": TIER_WORK,
        "id": work.id,
        "title": work.title,
        "sort_title": work.sort_title,
        "creators": creator_names,
        "expression_count": expression_count,
        "genres": meta.get("genres") or meta.get("genre"),
        "description_present": bool(meta.get("description") or meta.get("summary")),
    }


def describe_expression(expression: Expression) -> dict[str, Any]:
    """Summarize an Expression for LLM prompts and review-queue rendering.

    Args:
        expression: Expression to describe.

    Returns:
        JSON-serializable summary including child manifestation count and creators.
    """
    manifestation_count = len(expression.manifestations)
    label = (
        expression.label
        if hasattr(expression, "label") and expression.label
        else ((expression.meta.get("label") or expression.meta.get("title")) if isinstance(expression.meta, dict) else None)
    )
    return {
        "tier": TIER_EXPRESSION,
        "id": expression.id,
        "label": label,
        "language": expression.language,
        "content_type": expression.content_type,
        "manifestation_count": manifestation_count,
        "creators": sorted(_expression_creators(expression)),
    }


def describe_manifestation(manifestation: Manifestation) -> dict[str, Any]:
    """Summarize a Manifestation for LLM prompts and review-queue rendering.

    ISBN-family identifiers are surfaced here because the Manifestation (FRBRoo
    F3) is the only tier entitled to carry them.

    Args:
        manifestation: Manifestation to describe.

    Returns:
        JSON-serializable summary including identifiers and child-collection size.
    """
    expression = manifestation.expression
    work = expression.work if expression is not None else None
    # ``items`` is a plain list relationship (lazy=True), so the child count
    # comes from the eagerly loaded collection rather than a query.
    item_count = len(manifestation.items)
    return {
        "tier": TIER_MANIFESTATION,
        "id": manifestation.id,
        "title": manifestation.title,
        "creators": sorted(_manifestation_creators(manifestation)),
        "isbn13": manifestation.isbn13,
        "ean": manifestation.ean,
        "upc": manifestation.upc,
        "barcode": manifestation.barcode,
        "format": manifestation.format or manifestation.format_type,
        "publisher": manifestation.publisher,
        "publication_date": manifestation.publication_date.isoformat() if manifestation.publication_date else None,
        "label": manifestation.label,
        "catalog_number": manifestation.catalog_number,
        "language": expression.language if expression is not None else None,
        "content_type": expression.content_type if expression is not None else None,
        "work_title": work.title if work is not None else None,
        "work_id": work.id if work is not None else None,
        "item_count": item_count,
        "cover_url": manifestation.cover_url,
    }


# ---------------------------------------------------------------------------
# Local LLM (Ollama) client
# ---------------------------------------------------------------------------


def ollama_base_url() -> str:
    """Return the configured Ollama base URL without a trailing slash."""
    return os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")


def ollama_model() -> str:
    """Return the configured local model used for duplicate evaluation."""
    return os.environ.get("OLLAMA_DEDUPE_MODEL", DEFAULT_OLLAMA_MODEL)


def check_ollama_health() -> tuple[bool, str]:
    """Probe the local Ollama service and confirm the configured model is present.

    Called before a detection run so a missing prerequisite is reported as a
    clear setup message instead of surfacing as per-pair inference failures.

    Returns:
        Tuple of ``(healthy, message)``.  ``message`` is suitable for printing.
    """
    url = ollama_base_url()
    model = ollama_model()
    try:
        response = requests.get(f"{url}/api/tags", timeout=OLLAMA_HEALTH_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        return False, f"Ollama unreachable at {url} ({type(exc).__name__}). Start Ollama or set OLLAMA_URL."
    except ValueError as exc:
        return False, f"Ollama at {url} returned a non-JSON response ({type(exc).__name__})."

    names = [str(entry.get("name", "")) for entry in payload.get("models", []) if isinstance(entry, dict)]
    if model not in names:
        available = ", ".join(sorted(names)[:5]) or "none"
        return False, f"Ollama model '{model}' is not installed at {url} (available: {available}). Run 'ollama pull {model}'."
    return True, f"Ollama reachable at {url} with model '{model}'."


_SYSTEM_PROMPT = (
    "You are a meticulous bibliographic duplicate detector for an FRBR library catalog. "
    "You compare two catalog entities and decide whether they describe the same intellectual "
    "Work (for the 'work' tier), the same realization (for the 'expression' tier), or the same published edition (for the 'manifestation' tier). "
    "Different editions, different languages, different translations, or sequel volumes are NOT "
    "duplicates. "
    "Respond with a single JSON object and nothing else, using exactly this shape: "
    '{"verdict": true or false, "confidence": 0.0-1.0, "reasoning": "one or two sentences"}. '
    "confidence is the probability that the two entities are the same, not how well written the "
    "answer is. Base your judgement only on the supplied metadata."
)


def _build_prompt(tier: str, left: dict[str, Any], right: dict[str, Any]) -> str:
    """Render the pairwise comparison prompt for a candidate pair.

    Args:
        tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        left: Summary of the first entity.
        right: Summary of the second entity.

    Returns:
        The user-turn prompt text.
    """
    if tier == TIER_WORK:
        entity = "intellectual Work"
    elif tier == TIER_EXPRESSION:
        entity = "Expression realization"
    else:
        entity = "published Manifestation (edition)"
    return (
        f"Decide whether these two {entity} records are duplicates of each other.\n\n"
        f"Record A:\n{json.dumps(left, ensure_ascii=False, sort_keys=True)}\n\n"
        f"Record B:\n{json.dumps(right, ensure_ascii=False, sort_keys=True)}\n\n"
        "Answer with the JSON object described in your instructions."
    )


@dataclass(frozen=True)
class DuplicateEvaluation:
    """A single LLM verdict for one candidate pair."""

    verdict: bool
    confidence: float
    reasoning: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the verdict for API responses."""
        return asdict(self)


def _coerce_confidence(raw: Any) -> float | None:
    """Clamp an LLM-supplied confidence into the closed interval ``[0.0, 1.0]``.

    Args:
        raw: Value reported by the model.

    Returns:
        Clamped float, or ``None`` when the value is not numeric.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN
        return None
    return min(1.0, max(0.0, value))


def parse_evaluation(content: str) -> DuplicateEvaluation:
    """Parse and validate the structured JSON verdict returned by the LLM.

    Markdown fences are tolerated because local models frequently wrap JSON
    despite the structured-output request.

    Args:
        content: Raw ``message.content`` text from the Ollama chat response.

    Returns:
        Validated :class:`DuplicateEvaluation`.

    Raises:
        DuplicateEvaluationError: If the payload is not JSON, lacks a numeric
            confidence, or lacks a textual rationale.
    """
    if not content or not content.strip():
        raise DuplicateEvaluationError("Ollama returned an empty response")

    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise DuplicateEvaluationError(f"Ollama response was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise DuplicateEvaluationError("Ollama response JSON was not an object")

    confidence = _coerce_confidence(payload.get("confidence"))
    if confidence is None:
        raise DuplicateEvaluationError("Ollama response did not include a numeric 'confidence'")

    reasoning = payload.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise DuplicateEvaluationError("Ollama response did not include a textual 'reasoning'")

    raw_verdict = payload.get("verdict")
    if isinstance(raw_verdict, str):
        verdict = raw_verdict.strip().lower() in {"true", "yes", "duplicate", "match"}
    else:
        verdict = bool(raw_verdict)

    return DuplicateEvaluation(verdict=verdict, confidence=confidence, reasoning=reasoning.strip())


def evaluate_pair_with_llm(tier: str, left: dict[str, Any], right: dict[str, Any]) -> DuplicateEvaluation:
    """Ask the local LLM whether two entity summaries are duplicates.

    Args:
        tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        left: Summary of the first entity.
        right: Summary of the second entity.

    Returns:
        The parsed :class:`DuplicateEvaluation`.

    Raises:
        DuplicateEvaluationError: If Ollama is unreachable, errors, or returns an
            unparseable payload.  Callers are expected to log and continue so a
            single bad response never aborts a whole detection run.
    """
    url = ollama_base_url()
    model = ollama_model()
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(tier, left, right)},
        ],
    }
    try:
        response = requests.post(f"{url}/api/chat", json=payload, timeout=OLLAMA_TIMEOUT_SECONDS)
        response.raise_for_status()
        body = response.json()
    except requests.exceptions.RequestException as exc:
        raise DuplicateEvaluationError(f"Ollama request failed: {type(exc).__name__}: {exc}") from exc
    except ValueError as exc:
        raise DuplicateEvaluationError(f"Ollama returned a non-JSON response: {type(exc).__name__}") from exc

    message = body.get("message") if isinstance(body, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise DuplicateEvaluationError("Ollama response did not contain a chat message content field")
    return parse_evaluation(content)


# ---------------------------------------------------------------------------
# Heuristic candidate screening
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScreenedPair:
    """A heuristic candidate pair awaiting LLM verification."""

    entity_tier: str
    left_id: int
    right_id: int
    heuristic_score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)


def _blocking_keys(tier: str, entity: Any) -> list[tuple[str, str]]:
    """Return cheap blocking keys that group likely duplicates together.

    Blocking keeps the screening stage near-linear: instead of comparing every
    entity with every other entity, only entities that share at least one key
    are ever compared.

    Args:
        tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        entity: Work, Expression, or Manifestation to derive keys from.

    Returns:
        List of ``(key_name, key_value)`` tuples; may be empty.
    """
    keys: list[tuple[str, str]] = []

    if tier == TIER_WORK:
        title = normalize_title(entity.title)
        sort_title = normalize_title(entity.sort_title)
        if title:
            keys.append(("title", title))
            if len(title) >= 5:
                keys.append(("title_prefix", title[:5]))
                # Long titles ("the lord of the rings the two towers") share a
                # prefix but differ later; an inverted token key catches those.
                tail = title.split()[-2:]
                if len(tail) == 2:
                    keys.append(("title_suffix", " ".join(tail)))
        if sort_title:
            keys.append(("sort_title", sort_title))
    elif tier == TIER_EXPRESSION:
        label = (
            entity.label
            if hasattr(entity, "label") and entity.label
            else ((entity.meta.get("label") or entity.meta.get("title")) if isinstance(entity.meta, dict) else None)
        )
        norm_label = normalize_title(label)
        lang = entity.language or ""
        ctype = entity.content_type or ""
        if norm_label:
            keys.append(("expr_label_lang_type", f"{norm_label}|{lang}|{ctype}"))
    else:
        title = normalize_title(entity.title)
        if title:
            keys.append(("title", title))
            if len(title) >= 5:
                keys.append(("title_prefix", title[:5]))
        for attribute in ("isbn13", "ean", "upc", "barcode"):
            value = getattr(entity, attribute, None)
            if value:
                # ISBN/UPC are edition-defining on the Manifestation (F3); a
                # shared identifier is near-conclusive evidence.
                keys.append((attribute, str(value)))

    return keys


def _iter_entity_pages(model: type[Any], tier: str, start_id: int, page_size: int) -> list[Any]:
    """Load one bounded keyset page of catalog entities.

    Detection must never call ``.all()`` on an unbounded query, so entities are
    read in stable primary-key order using keyset pagination.

    Args:
        model: Work or Manifestation model class.
        tier: Entity tier, used to pick eager-loading options.
        start_id: Exclusive lower bound on the primary key.
        page_size: Maximum rows to return.

    Returns:
        List of at most ``page_size`` entities ordered by ascending id.
    """
    stmt: Select = select(model).where(model.id > start_id).order_by(model.id).limit(page_size)
    # Loader keys are written as model attributes; the stub types for
    # ``selectinload`` reject the string form even though SQLAlchemy accepts it.
    if tier == TIER_WORK:
        stmt = stmt.options(
            selectinload(Work.contributions).selectinload(WorkContribution.contributor),
            selectinload(Work.expressions),
        )
    elif tier == TIER_EXPRESSION:
        stmt = stmt.options(
            selectinload(Expression.work).selectinload(Work.contributions).selectinload(WorkContribution.contributor),
            selectinload(Expression.contributions).selectinload(ExpressionContribution.contributor),
            selectinload(Expression.manifestations),
        )
    else:
        # ``Manifestation.contributions`` is a ``lazy="dynamic"`` backref and
        # therefore rejects eager loading; it is read on demand by
        # :func:`_manifestation_creators`, which only runs for pairs that have
        # already survived blocking.  ``items`` is a plain list relationship and
        # is loaded here so the child count does not add a query per row.
        stmt = stmt.options(
            selectinload(Manifestation.expression).selectinload(Expression.work),
            selectinload(Manifestation.items),
        )

    return list(db.session.execute(stmt).scalars().all())


#: A blocking bucket larger than this is a degenerate value (a near-empty shared
#: prefix, or a placeholder identifier reused across the catalog) and would cost
#: quadratically to expand, so it is skipped rather than stalling the run.
MAX_BLOCK_SIZE: int = 40


def _screen_page(tier: str, entities: list[Any]) -> list[ScreenedPair]:
    """Find heuristically similar pairs within one loaded page.

    Args:
        tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        entities: Entities from a single keyset page.

    Returns:
        Screened candidate pairs, each with the signals that triggered it.
    """
    blocks: dict[tuple[str, str], list[Any]] = {}
    for entity in entities:
        for key in _blocking_keys(tier, entity):
            blocks.setdefault(key, []).append(entity)

    seen: set[tuple[int, int]] = set()
    pairs: list[ScreenedPair] = []

    for key, members in blocks.items():
        if len(members) < 2 or len(members) > MAX_BLOCK_SIZE:
            continue
        for index, left in enumerate(members):
            for right in members[index + 1 :]:
                left_id, right_id = left.id, right.id
                pair_key = (min(left_id, right_id), max(left_id, right_id))
                if pair_key in seen:
                    continue
                score, reasons = _score_pair(tier, left, right, key)
                if score <= 0.0:
                    continue
                seen.add(pair_key)
                pairs.append(
                    ScreenedPair(
                        entity_tier=tier,
                        left_id=left_id,
                        right_id=right_id,
                        heuristic_score=score,
                        reasons=tuple(reasons),
                    )
                )

    pairs.sort(key=lambda pair: pair.heuristic_score, reverse=True)
    return pairs


def _score_pair(tier: str, left: Any, right: Any, block_key: tuple[str, str]) -> tuple[float, list[str]]:
    """Score one pair from the signals available on the loaded entities.

    Args:
        tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        left: First entity.
        right: Second entity.
        block_key: The blocking key that put both entities in the same bucket.

    Returns:
        Tuple of ``(score, reasons)``; ``score`` is ``0.0`` when the pair should
        not reach the LLM at all.
    """
    reasons: list[str] = []
    score = 0.0

    if tier == TIER_EXPRESSION:
        # Cross-language or cross-content_type pairs are discarded before scoring
        if (left.language or None) != (right.language or None) or (left.content_type or None) != (right.content_type or None):
            return 0.0, []

        left_label = (
            left.label
            if hasattr(left, "label") and left.label
            else ((left.meta.get("label") or left.meta.get("title")) if isinstance(left.meta, dict) else None)
        )
        right_label = (
            right.label
            if hasattr(right, "label") and right.label
            else ((right.meta.get("label") or right.meta.get("title")) if isinstance(right.meta, dict) else None)
        )
        norm_left = normalize_title(left_label)
        norm_right = normalize_title(right_label)
        if not norm_left or not norm_right:
            return 0.0, []

        similarity = title_similarity(left_label, right_label)
        if similarity >= TITLE_SIMILARITY_FLOOR:
            score = max(score, similarity)
            reasons.append(f"label similarity {similarity:.2f}")

        left_creators = _expression_creators(left)
        right_creators = _expression_creators(right)
        overlap = left_creators & right_creators
        if overlap:
            score = max(score, 0.75)
            reasons.append(f"shared creator(s): {', '.join(sorted(overlap))}")

        if score <= 0.0:
            return 0.0, []
        reasons.append(f"blocked on {block_key[0]}")
        return min(score, 1.0), reasons

    if tier == TIER_MANIFESTATION:
        for attribute in ("isbn13", "ean", "upc", "barcode"):
            left_value = getattr(left, attribute, None)
            right_value = getattr(right, attribute, None)
            if left_value and left_value == right_value:
                # A shared ISBN means the same edition, full stop.
                return 1.0, [f"identical {attribute}"]

    similarity = title_similarity(left.title, right.title)
    sort_similarity = title_similarity(getattr(left, "sort_title", None), getattr(right, "sort_title", None))
    if similarity >= TITLE_SIMILARITY_FLOOR:
        score = max(score, similarity)
        reasons.append(f"title similarity {similarity:.2f}")

    left_creators = work_creators(left) if tier == TIER_WORK else _manifestation_creators(left)
    right_creators = work_creators(right) if tier == TIER_WORK else _manifestation_creators(right)
    overlap = left_creators & right_creators
    if overlap:
        score = max(score, 0.75)
        reasons.append(f"shared creator(s): {', '.join(sorted(overlap))}")

    if overlap and sort_similarity >= SORT_TITLE_FLOOR_WITH_CREATOR_OVERLAP:
        score = max(score, 0.8)
        reasons.append(f"sort title similarity {sort_similarity:.2f}")

    if score <= 0.0:
        return 0.0, []
    reasons.append(f"blocked on {block_key[0]}")
    return min(score, 1.0), reasons


def classify_pair(tier: str, left: Any, right: Any) -> tuple[str, list[str]]:
    """Decide a screened pair without consulting a language model.

    The two-stage pipeline exists because most pairs can be settled by rules
    alone, and the expensive stage was doing far less than its design implied.
    Measured on a production clone, the ``0.75`` creator-overlap rule in
    :func:`_score_pair` is what admits pairs like *Neuromancer* vs *Snow Crash* --
    two different books by the same author -- so the language model was mostly
    acting as a same-author noise filter.  Meanwhile a pair sharing an edition
    identifier is already conclusive, yet was still paying for a call.

    Outcomes:

    * ``AUTO_ACCEPT`` -- a shared edition identifier (Manifestation tier), an
      identical normalized label with matching language and content_type (Expression tier),
      or an identical normalized title corroborated by a shared creator (Work tier).
      Queued without consulting :attr:`DEFAULT_THRESHOLD`, because a categorical
      match should not need a probability gate.
    * ``AUTO_REJECT`` -- a shared creator whose titles fail the similarity floor,
      which is the same-author noise described above.
    * ``NEEDS_LLM``  -- the genuine grey zone, only adjudicated under the
      ``llama`` engine.

    Args:
        tier: ``"work"``, ``"expression"``, or ``"manifestation"``.
        left: First entity of the pair.
        right: Second entity of the pair.

    Returns:
        Tuple of ``(classification, reasons)``; reasons are stored as the
        candidate's rationale when no model was consulted.
    """
    reasons: list[str] = []

    if tier == TIER_EXPRESSION:
        if (left.language or None) != (right.language or None) or (left.content_type or None) != (right.content_type or None):
            return CLASSIFICATION_AUTO_REJECT, ["different language or content_type"]

        left_label = (
            left.label
            if hasattr(left, "label") and left.label
            else ((left.meta.get("label") or left.meta.get("title")) if isinstance(left.meta, dict) else None)
        )
        right_label = (
            right.label
            if hasattr(right, "label") and right.label
            else ((right.meta.get("label") or right.meta.get("title")) if isinstance(right.meta, dict) else None)
        )
        norm_left = normalize_title(left_label)
        norm_right = normalize_title(right_label)

        if bool(norm_left) and norm_left == norm_right:
            return CLASSIFICATION_AUTO_ACCEPT, [
                "identical normalized label",
                f"matching language ({left.language}) and content_type ({left.content_type})",
            ]

        similarity = title_similarity(left_label, right_label)
        creators = _creators_for_tier(tier, left) & _creators_for_tier(tier, right)

        if creators and similarity < TITLE_SIMILARITY_FLOOR:
            return (
                CLASSIFICATION_AUTO_REJECT,
                [f"shared creator(s) {', '.join(sorted(creators))} but label similarity {similarity:.2f} is below the floor"],
            )

        reasons.append(f"label similarity {similarity:.2f}")
        if creators:
            reasons.append(f"shared creator(s): {', '.join(sorted(creators))}")
        return CLASSIFICATION_NEEDS_LLM, reasons

    if tier == TIER_MANIFESTATION:
        for attribute in CONCLUSIVE_EDITION_IDENTIFIERS:
            left_value = getattr(left, attribute, None)
            if left_value and left_value == getattr(right, attribute, None):
                return CLASSIFICATION_AUTO_ACCEPT, [f"identical {attribute}"]

    similarity = title_similarity(left.title, right.title)
    identical_title = bool(normalize_title(left.title)) and normalize_title(left.title) == normalize_title(right.title)
    creators = _creators_for_tier(tier, left) & _creators_for_tier(tier, right)

    if identical_title and creators:
        # Two catalog entries that normalize to exactly the same title *and*
        # share an author are the same work.  A title match alone is not enough:
        # the production clone holds six distinct works titled "Greatest Hits".
        return CLASSIFICATION_AUTO_ACCEPT, ["identical normalized title", f"shared creator(s): {', '.join(sorted(creators))}"]

    if creators and similarity < TITLE_SIMILARITY_FLOOR:
        return (
            CLASSIFICATION_AUTO_REJECT,
            [f"shared creator(s) {', '.join(sorted(creators))} but title similarity {similarity:.2f} is below the floor"],
        )

    reasons.append(f"title similarity {similarity:.2f}")
    if creators:
        reasons.append(f"shared creator(s): {', '.join(sorted(creators))}")
    return CLASSIFICATION_NEEDS_LLM, reasons


def _creators_for_tier(tier: str, entity: Any) -> set[str]:
    """Return the normalized creator set for an entity at any tier.

    Args:
        tier: ``"work"``, ``"expression"``, or ``"manifestation"``.
        entity: Work, Expression, or Manifestation.

    Returns:
        Normalized creator names, possibly empty.
    """
    if tier == TIER_WORK:
        return work_creators(entity)
    if tier == TIER_EXPRESSION:
        return _expression_creators(entity)
    return _manifestation_creators(entity)


def classify_pair_by_id(tier: str, left_id: int, right_id: int) -> tuple[str, list[str]]:
    """Load two entities and classify the pair, tolerating a missing row.

    Args:
        tier: ``"work"``, ``"expression"``, or ``"manifestation"``.
        left_id: Primary key of the first entity.
        right_id: Primary key of the second entity.

    Returns:
        Tuple of ``(classification, reasons)``; a pair whose entities have since
        been deleted is reported as needing the model rather than raising.
    """
    if tier == TIER_WORK:
        model = Work
    elif tier == TIER_EXPRESSION:
        model = Expression
    else:
        model = Manifestation
    left = db.session.get(model, left_id)
    right = db.session.get(model, right_id)
    if left is None or right is None:
        return CLASSIFICATION_NEEDS_LLM, ["one of the entities no longer exists"]
    return classify_pair(tier, left, right)


def _manifestation_creators(manifestation: Manifestation) -> set[str]:
    """Return the normalized creator set reachable from a Manifestation.

    Prefers the parent Work's authors (FRBR: creators belong to the Work) and
    falls back to the manifestation's own publication contributions.

    Args:
        manifestation: Manifestation to inspect.

    Returns:
        Set of normalized creator names.
    """
    work = manifestation.expression.work if manifestation.expression is not None else None
    if work is not None:
        creators = work_creators(work)
        if creators:
            return creators
    return contribution_creators(list(manifestation.contributions or []))


def _existing_pair_ids(tier: str) -> dict[tuple[int, int], DuplicateCandidate]:
    """Return already-registered pairs for a tier, keyed order-insensitively.

    A pair that was previously dismissed or merged must never be re-queued, so
    every existing row is loaded once and consulted in memory rather than issuing
    a query per pair.

    Args:
        tier: Entity tier to load candidates for.

    Returns:
        Mapping of ``(low_id, high_id)`` to the existing candidate row.
    """
    rows = db.session.execute(select(DuplicateCandidate).where(DuplicateCandidate.entity_tier == tier)).scalars().all()
    return {(min(row.source_id, row.target_id), max(row.source_id, row.target_id)): row for row in rows}


# ---------------------------------------------------------------------------
# Candidate persistence and lifecycle
# ---------------------------------------------------------------------------


def get_candidate(candidate_id: int) -> DuplicateCandidate | None:
    """Return a candidate by primary key, or ``None`` when absent.

    Args:
        candidate_id: Primary key of the candidate row.

    Returns:
        The candidate or ``None``.
    """
    return db.session.get(DuplicateCandidate, candidate_id)


def find_existing_pair(entity_tier: str, left_id: int, right_id: int) -> DuplicateCandidate | None:
    """Return the candidate registered for an unordered entity pair, if any.

    Args:
        entity_tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        left_id: First entity id.
        right_id: Second entity id.

    Returns:
        The existing candidate, or ``None``.
    """
    low, high = min(left_id, right_id), max(left_id, right_id)
    return db.session.execute(
        select(DuplicateCandidate).where(
            DuplicateCandidate.entity_tier == entity_tier,
            DuplicateCandidate.source_id == low,
            DuplicateCandidate.target_id == high,
        )
    ).scalar_one_or_none()


def record_candidate(
    entity_tier: str,
    source_id: int,
    target_id: int,
    confidence: float | None,
    reasoning: str,
    resolution_source: str = DUPLICATE_RESOLUTION_LLAMA,
) -> DuplicateCandidate | None:
    """Persist a pending candidate, skipping pairs that are already registered.

    The pair is stored in canonical ``(low, high)`` order so the order-insensitive
    unique index rejects reverse-order duplicates at the database level.

    Args:
        entity_tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        source_id: First entity id.
        target_id: Second entity id.
        confidence: Match probability in ``[0.0, 1.0]``, or ``None`` for a
            candidate the deterministic classifier queued without a score.
        reasoning: LLM rationale, or the classifier's reasons when no model was
            consulted.
        resolution_source: Which stage decided the pair.  See
            :data:`DUPLICATE_RESOLUTION_SOURCES`.

    Returns:
        The new candidate, or ``None`` when the pair was already registered.

    Raises:
        DuplicateServiceError: If the arguments are structurally invalid.
    """
    if entity_tier not in DUPLICATE_ENTITY_TIERS:
        raise DuplicateServiceError(f"Unsupported entity tier: {entity_tier!r}")
    if source_id == target_id:
        raise DuplicateServiceError("Cannot create a duplicate candidate for an entity paired with itself")
    if resolution_source not in DUPLICATE_RESOLUTION_SOURCES:
        raise DuplicateServiceError(f"Unsupported resolution source: {resolution_source!r}")

    low, high = min(source_id, target_id), max(source_id, target_id)
    if find_existing_pair(entity_tier, low, high) is not None:
        return None

    candidate = DuplicateCandidate(
        entity_tier=entity_tier,
        source_id=low,
        target_id=high,
        confidence=None if confidence is None else min(1.0, max(0.0, float(confidence))),
        llm_reasoning=reasoning,
        resolution_source=resolution_source,
        status=DUPLICATE_STATUS_PENDING,
    )
    db.session.add(candidate)
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        # A concurrent detection run may have inserted the same pair first; the
        # unique index is the final arbiter, so treat the collision as "already
        # known" rather than as a failure.
        if find_existing_pair(entity_tier, low, high) is not None:
            return None
        raise
    return candidate


def dismiss_candidate(candidate: DuplicateCandidate, user_id: UUID | None) -> DuplicateCandidate:
    """Mark a candidate as a false positive and record who decided so.

    Args:
        candidate: Candidate to dismiss.
        user_id: UUID of the acting administrator.

    Returns:
        The updated candidate.

    Raises:
        DuplicateServiceError: If the candidate was already resolved.
    """
    if candidate.status != DUPLICATE_STATUS_PENDING:
        raise DuplicateServiceError(f"Candidate {candidate.id} is already resolved (status={candidate.status})")
    candidate.status = DUPLICATE_STATUS_DISMISSED
    candidate.resolved_at = datetime.now(UTC)
    candidate.resolved_by_id = user_id
    db.session.add(candidate)
    db.session.commit()
    return candidate


def list_candidates(
    *,
    status: str | None = DUPLICATE_STATUS_PENDING,
    entity_tier: str | None = None,
    min_confidence: float | None = None,
    page: int = 1,
    limit: int = 25,
) -> tuple[list[DuplicateCandidate], int]:
    """Return one page of candidates plus the total matching count.

    Filtering and pagination happen in SQL; the result set is never sliced in
    Python.

    Args:
        status: Lifecycle status filter, or ``None`` for all statuses.
        entity_tier: ``"work"``, ``"expression"``, ``"manifestation"``, or ``None`` for all.
        min_confidence: Inclusive lower bound on confidence, or ``None``.
        page: 1-based page number.
        limit: Page size, clamped to ``1..QUEUE_PAGE_SIZE_LIMIT``.

    Returns:
        Tuple of ``(candidates, total)``.

    Raises:
        DuplicateServiceError: If a filter value is not part of its vocabulary.
    """
    if status is not None and status not in {DUPLICATE_STATUS_PENDING, DUPLICATE_STATUS_MERGED, DUPLICATE_STATUS_DISMISSED}:
        raise DuplicateServiceError(f"Unknown status filter: {status!r}")
    if entity_tier is not None and entity_tier not in DUPLICATE_ENTITY_TIERS:
        raise DuplicateServiceError(f"Unknown entity tier filter: {entity_tier!r}")

    page = max(1, int(page))
    limit = min(max(1, int(limit)), QUEUE_PAGE_SIZE_LIMIT)
    offset = (page - 1) * limit

    filters = []
    if status is not None:
        filters.append(DuplicateCandidate.status == status)
    if entity_tier is not None:
        filters.append(DuplicateCandidate.entity_tier == entity_tier)
    if min_confidence is not None:
        filters.append(DuplicateCandidate.confidence >= min(1.0, max(0.0, float(min_confidence))))

    total = db.session.execute(select(func.count(DuplicateCandidate.id)).where(*filters)).scalar_one()
    rows = (
        db.session.execute(
            select(DuplicateCandidate)
            .where(*filters)
            .order_by(DuplicateCandidate.confidence.desc(), DuplicateCandidate.id)
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


# ---------------------------------------------------------------------------
# Detection run
# ---------------------------------------------------------------------------


@dataclass
class DetectionReport:
    """Outcome counters for a single detection run."""

    tier: str = TIER_ALL
    threshold: float = DEFAULT_THRESHOLD
    dry_run: bool = False
    engine: str = DEFAULT_ENGINE
    entities_screened: int = 0
    candidate_pairs: int = 0
    llm_evaluations: int = 0
    llm_failures: int = 0
    below_threshold: int = 0
    already_known: int = 0
    created: int = 0
    #: Pairs the deterministic classifier accepted outright, with no model
    #: consulted and no confidence threshold applied.
    auto_accepted: int = 0
    #: Pairs the classifier dismissed as same-author noise.
    auto_rejected: int = 0
    #: Pairs left undecided because the engine cannot classify them.  Under the
    #: ``heuristic`` engine these are the grey zone, and re-running with
    #: ``--engine llama`` is what adjudicates them.
    needs_llm: int = 0
    #: Candidates a dry run *would* have persisted.  Kept separate from
    #: :attr:`created` so an operator can never read a dry-run summary as if
    #: rows had actually been written.
    would_create: int = 0
    work_candidates: int = 0
    expression_candidates: int = 0
    manifestation_candidates: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report for CLI output and API responses."""
        return asdict(self)


def _resolve_tiers(tier: str) -> tuple[str, ...]:
    """Expand a ``--tier`` argument into concrete tiers to scan.

    Args:
        tier: One of ``"work"``, ``"expression"``, ``"manifestation"``, or ``"all"``.

    Returns:
        Tuple of tiers to process.

    Raises:
        DuplicateServiceError: If the tier argument is not recognized.
    """
    if tier not in _DETECTION_TIERS:
        raise DuplicateServiceError(f"Unknown tier: {tier!r}. Expected one of {sorted(_DETECTION_TIERS)}")
    return DUPLICATE_ENTITY_TIERS if tier == TIER_ALL else (tier,)


def _iter_screened_pairs(tier: str, limit: int | None, progress: Callable[[str], None] | None) -> Iterator[ScreenedPair]:
    """Yield heuristic candidate pairs for a tier, scanning in bounded pages.

    Args:
        tier: Entity tier to screen.
        limit: Maximum number of catalog entities to load, or ``None`` for all.
        progress: Optional progress reporter.

    Yields:
        :class:`ScreenedPair` instances in descending heuristic-score order.
    """
    if tier == TIER_WORK:
        model = Work
    elif tier == TIER_EXPRESSION:
        model = Expression
    else:
        model = Manifestation
    last_id = 0
    loaded = 0
    while limit is None or loaded < limit:
        page_size = SCAN_PAGE_SIZE if limit is None else min(SCAN_PAGE_SIZE, limit - loaded)
        page = _iter_entity_pages(model, tier, last_id, page_size)
        if not page:
            return
        last_id = page[-1].id
        loaded += len(page)
        if progress is not None:
            progress(f"[{tier}] screened {loaded} entities (through id {last_id})")
        yield from _screen_page(tier, page)
        if len(page) < page_size:
            return


def _describe_for_tier(tier: str, entity_id: int) -> dict[str, Any] | None:
    """Load and summarize an entity for the LLM prompt.

    Args:
        tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        entity_id: Primary key of the entity.

    Returns:
        The summary, or ``None`` when the entity no longer exists.
    """
    if tier == TIER_WORK:
        work = db.session.execute(
            select(Work).options(selectinload(Work.contributions).selectinload(WorkContribution.contributor)).where(Work.id == entity_id)
        ).scalar_one_or_none()
        return describe_work(work) if work is not None else None

    if tier == TIER_EXPRESSION:
        expression = db.session.execute(
            select(Expression)
            .options(
                selectinload(Expression.work).selectinload(Work.contributions).selectinload(WorkContribution.contributor),
                selectinload(Expression.contributions).selectinload(ExpressionContribution.contributor),
                selectinload(Expression.manifestations),
            )
            .where(Expression.id == entity_id)
        ).scalar_one_or_none()
        return describe_expression(expression) if expression is not None else None

    manifestation = db.session.execute(
        select(Manifestation)
        .options(
            selectinload(Manifestation.expression).selectinload(Expression.work),
            selectinload(Manifestation.items),
        )
        .where(Manifestation.id == entity_id)
    ).scalar_one_or_none()
    return describe_manifestation(manifestation) if manifestation is not None else None


def run_detection(
    *,
    tier: str = TIER_ALL,
    threshold: float = DEFAULT_THRESHOLD,
    limit: int | None = None,
    dry_run: bool = False,
    engine: str = DEFAULT_ENGINE,
    progress: Callable[[str], None] | None = None,
) -> DetectionReport:
    """Screen the catalog and queue verified duplicate candidates for review.

    Pairs that already have a candidate row in any status are skipped, so
    previously dismissed false positives and completed merges are never
    re-queued.  LLM failures are recorded and skipped rather than raised, so a
    temporarily unavailable Ollama never blocks catalog operations.

    Args:
        tier: ``"work"``, ``"expression"``, ``"manifestation"``, or ``"all"``.
        threshold: Minimum LLM confidence required to queue an undecided pair.
            Not applied to a pair the classifier accepted categorically.
        limit: Maximum number of catalog entities to load per tier, or ``None``.
        dry_run: Evaluate and report without writing candidate rows.
        engine: ``"heuristic"`` (default) never contacts a model; ``"llama"``
            also adjudicates the grey zone the classifier cannot decide.
        progress: Optional callable receiving human-readable progress lines.

    Returns:
        A :class:`DetectionReport` describing the run.

    Raises:
        DuplicateServiceError: If the tier, threshold, or engine argument is
            invalid.
    """
    if not 0.0 <= float(threshold) <= 1.0:
        raise DuplicateServiceError(f"threshold must be between 0.0 and 1.0, got {threshold}")
    if limit is not None and limit <= 0:
        raise DuplicateServiceError(f"limit must be a positive integer, got {limit}")
    if engine not in DETECTION_ENGINES:
        raise DuplicateServiceError(f"Unknown engine: {engine!r}. Expected one of {sorted(DETECTION_ENGINES)}")

    report = DetectionReport(tier=tier, threshold=float(threshold), dry_run=dry_run, engine=engine)
    use_llm = engine == ENGINE_LLAMA

    for active_tier in _resolve_tiers(tier):
        known = _existing_pair_ids(active_tier)
        evaluations = 0

        for pair in _iter_screened_pairs(active_tier, limit, progress):
            report.candidate_pairs += 1
            if active_tier == TIER_WORK:
                report.work_candidates += 1
            elif active_tier == TIER_EXPRESSION:
                report.expression_candidates += 1
            else:
                report.manifestation_candidates += 1

            pair_key = (min(pair.left_id, pair.right_id), max(pair.left_id, pair.right_id))
            if pair_key in known:
                report.already_known += 1
                continue

            # Deterministic classification first.  It resolves the two categories
            # that need no model at all -- a categorical match, and same-author
            # noise -- and leaves only the grey zone to inference.
            classification, reasons = classify_pair_by_id(active_tier, pair.left_id, pair.right_id)
            heuristic_reasons = list(reasons) + [reason for reason in pair.reasons if reason not in reasons]

            if classification == CLASSIFICATION_AUTO_REJECT:
                report.auto_rejected += 1
                if progress is not None:
                    progress(f"[{active_tier}] rejected ({pair.left_id}, {pair.right_id}): {'; '.join(reasons)}")
                continue

            if classification == CLASSIFICATION_AUTO_ACCEPT:
                report.auto_accepted += 1
                created = None
                if dry_run:
                    report.would_create += 1
                else:
                    created = record_candidate(
                        active_tier,
                        pair.left_id,
                        pair.right_id,
                        None,
                        "heuristic: " + "; ".join(heuristic_reasons),
                        resolution_source=DUPLICATE_RESOLUTION_HEURISTIC,
                    )
                    if created is None:
                        report.already_known += 1
                        continue
                    known[pair_key] = created
                    report.created += 1
                if progress is not None:
                    outcome = (
                        f"would queue ({pair.left_id}, {pair.right_id})"
                        if dry_run
                        else f"queued candidate #{created.id} ({pair.left_id}, {pair.right_id})"
                    )
                    progress(f"[{active_tier}] {outcome}: {'; '.join(reasons)}")
                continue

            # Grey zone: only the llama engine can settle it.
            report.needs_llm += 1
            if not use_llm:
                if progress is not None:
                    progress(
                        f"[{active_tier}] undecided ({pair.left_id}, {pair.right_id}); the heuristic engine "
                        f"will not guess -- re-run with --engine {ENGINE_LLAMA} to adjudicate"
                    )
                continue

            if evaluations >= MAX_LLM_EVALUATIONS_PER_RUN:
                if progress is not None:
                    progress(
                        f"[{active_tier}] per-run LLM evaluation cap ({MAX_LLM_EVALUATIONS_PER_RUN}) reached; remaining pairs deferred"
                    )
                continue

            left = _describe_for_tier(active_tier, pair.left_id)
            right = _describe_for_tier(active_tier, pair.right_id)
            if left is None or right is None:
                continue

            evaluations += 1
            report.llm_evaluations += 1
            try:
                evaluation = evaluate_pair_with_llm(active_tier, left, right)
            except DuplicateEvaluationError as exc:
                report.llm_failures += 1
                logger.warning("Duplicate evaluation failed for %s pair (%s, %s): %s", active_tier, pair.left_id, pair.right_id, exc)
                if progress is not None:
                    progress(f"[{active_tier}] evaluation failed for ({pair.left_id}, {pair.right_id}): {exc}")
                continue

            if not evaluation.verdict or evaluation.confidence < report.threshold:
                report.below_threshold += 1
                if progress is not None:
                    progress(
                        f"[{active_tier}] not queued ({pair.left_id}, {pair.right_id}): "
                        f"verdict={evaluation.verdict} confidence={evaluation.confidence:.2f} < threshold {report.threshold:.2f}"
                    )
                continue

            reasoning = f"{evaluation.reasoning} | heuristic: {', '.join(pair.reasons)}"
            if dry_run:
                report.would_create += 1
                if progress is not None:
                    progress(f"[{active_tier}] would queue ({pair.left_id}, {pair.right_id}) at confidence {evaluation.confidence:.2f}")
                continue

            created = record_candidate(
                active_tier,
                pair.left_id,
                pair.right_id,
                evaluation.confidence,
                reasoning,
                resolution_source=DUPLICATE_RESOLUTION_LLAMA,
            )
            if created is None:
                report.already_known += 1
                continue
            known[pair_key] = created
            report.created += 1
            if progress is not None:
                progress(
                    f"[{active_tier}] queued candidate #{created.id} for ({pair.left_id}, {pair.right_id}) at confidence {evaluation.confidence:.2f}"
                )

    return report


# ---------------------------------------------------------------------------
# FRBR merge helpers
# ---------------------------------------------------------------------------


def _consolidate_meta(target_meta: Any, source_meta: Any) -> dict[str, Any]:
    """Merge two ``meta`` documents without overwriting curated target values.

    The surviving primary entity is authoritative: its keys win.  Keys present
    only on the discarded entity are carried over so no metadata is lost.

    Args:
        target_meta: Metadata of the surviving entity.
        source_meta: Metadata of the discarded entity.

    Returns:
        The merged metadata dictionary.
    """
    merged: dict[str, Any] = {}
    if isinstance(source_meta, dict):
        merged.update(source_meta)
    if isinstance(target_meta, dict):
        merged.update(target_meta)
    return merged


# ---------------------------------------------------------------------------
# Work merge
# ---------------------------------------------------------------------------


def merge_work(source: Work, target: Work, user_id: UUID | None) -> Work:
    """Consolidate a duplicate Work into a surviving Work, atomically.

    Re-parents every child Expression, reconciles Work contributions, WorkPart
    containment, and WorkExpansionLink edges, consolidates game container
    aggregations, feedback, notes, semantic links, roadmaps, and escalation
    requests, then removes the source Work.  Any failure rolls the whole
    transaction back, leaving both Works and all Expressions untouched.

    Args:
        source: Work to be removed.
        target: Work to survive.
        user_id: UUID of the acting administrator, recorded in the audit log.

    Returns:
        The surviving :class:`Work`.

    Raises:
        DuplicateServiceError: If the two Works are the same entity.
    """
    if source.id == target.id:
        raise DuplicateServiceError("Cannot merge a Work with itself")

    # Row locks hold until commit so a concurrent edit cannot interleave.
    locked = frbr_merge.lock_pair(Work, source.id, target.id)
    if len(locked) != 2:
        raise DuplicateServiceError("One of the Works no longer exists; the merge was aborted")

    try:
        repointed = frbr_merge.repoint_references(TIER_WORK, source.id, target.id)
        target.meta = _consolidate_meta(target.meta, source.meta)

        db.session.add(
            EntityAuditLog(
                entity_type=TIER_WORK,
                entity_id=source.id,
                actor_id=user_id,
                change_type="merge_work",
                diff={
                    "source_id": source.id,
                    "target_id": target.id,
                    "migrated_children": repointed.get("Expression.work_id", 0),
                    "migrated_contributions": repointed.get("WorkContribution.work_id", 0),
                    "repointed": repointed,
                },
            )
        )

        frbr_merge.delete_source_row(source)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return target


# ---------------------------------------------------------------------------
# Expression merge
# ---------------------------------------------------------------------------


def merge_expression(source: Expression, target: Expression, user_id: UUID | None) -> Expression:
    """Consolidate a duplicate Expression into a surviving Expression, atomically.

    Re-parents every child Manifestation, reconciles Expression contributions,
    feedback, notes, semantic links, roadmaps, and escalation requests,
    preserves user wishlist entries (``UserWorkIntent.expression_id``), then
    removes the source Expression.  Refuses cross-language or cross-content_type
    merges before writing, because those attributes define distinct realizations.

    Args:
        source: Expression to be removed.
        target: Expression to survive.
        user_id: UUID of the acting administrator, recorded in the audit log.

    Returns:
        The surviving :class:`Expression`.

    Raises:
        DuplicateServiceError: If the two Expressions are the same entity, or
            if their language or content_type differ.
    """
    if source.id == target.id:
        raise DuplicateServiceError("Cannot merge an Expression with itself")

    if source.language != target.language:
        raise DuplicateServiceError(f"Cannot merge Expressions with different languages: {source.language!r} vs {target.language!r}")
    if source.content_type != target.content_type:
        raise DuplicateServiceError(
            f"Cannot merge Expressions with different content types: {source.content_type!r} vs {target.content_type!r}"
        )

    locked = frbr_merge.lock_pair(Expression, source.id, target.id)
    if len(locked) != 2:
        raise DuplicateServiceError("One of the Expressions no longer exists; the merge was aborted")

    try:
        repointed = frbr_merge.repoint_references(TIER_EXPRESSION, source.id, target.id)
        target.meta = _consolidate_meta(target.meta, source.meta)

        db.session.add(
            EntityAuditLog(
                entity_type=TIER_EXPRESSION,
                entity_id=source.id,
                actor_id=user_id,
                change_type="merge_expression",
                diff={
                    "source_id": source.id,
                    "target_id": target.id,
                    "migrated_children": repointed.get("Manifestation.expression_id", 0),
                    "migrated_contributions": repointed.get("ExpressionContribution.expression_id", 0),
                    "repointed": repointed,
                },
            )
        )

        frbr_merge.delete_source_row(source)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return target


# ---------------------------------------------------------------------------
# Manifestation merge
# ---------------------------------------------------------------------------


def merge_manifestation(source: Manifestation, target: Manifestation, user_id: UUID | None) -> Manifestation:
    """Consolidate a duplicate Manifestation into a surviving Manifestation, atomically.

    Re-parents every child Item, reconciles publication contributions, image
    scans, feedback, notes, semantic links, roadmaps, escalation requests, and
    scan telemetry, consolidates ISBN-family identifiers strictly on the target
    Manifestation (FRBRoo F3), then removes the source.

    Args:
        source: Manifestation to be removed.
        target: Manifestation to survive.
        user_id: UUID of the acting administrator, recorded in the audit log.

    Returns:
        The surviving :class:`Manifestation`.

    Raises:
        DuplicateServiceError: If the two Manifestations are the same entity.
    """
    if source.id == target.id:
        raise DuplicateServiceError("Cannot merge a Manifestation with itself")

    locked = frbr_merge.lock_pair(Manifestation, source.id, target.id)
    if len(locked) != 2:
        raise DuplicateServiceError("One of the Manifestations no longer exists; the merge was aborted")

    try:
        repointed = frbr_merge.repoint_references(TIER_MANIFESTATION, source.id, target.id)
        target.meta = _consolidate_meta(target.meta, source.meta)
        source_isbn13 = source.isbn13
        frbr_merge.consolidate_manifestation_identifiers(target, source)

        db.session.add(
            EntityAuditLog(
                entity_type=TIER_MANIFESTATION,
                entity_id=source.id,
                actor_id=user_id,
                change_type="merge_manifestation",
                diff={
                    "source_id": source.id,
                    "target_id": target.id,
                    "migrated_children": repointed.get("Item.manifestation_id", 0),
                    "migrated_contributions": repointed.get("ManifestationContribution.manifestation_id", 0),
                    "repointed": repointed,
                    "adopted_source_isbn13": source_isbn13,
                    "target_isbn13": target.isbn13,
                },
            )
        )

        frbr_merge.delete_source_row(source)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return target


# ---------------------------------------------------------------------------
# Candidate resolution entry point
# ---------------------------------------------------------------------------


def resolve_candidate_merge(candidate: DuplicateCandidate, primary_entity_id: int, user_id: UUID | None) -> dict[str, Any]:
    """Merge a candidate's two entities, keeping ``primary_entity_id``.

    Args:
        candidate: Pending candidate describing the pair.
        primary_entity_id: Id of the entity to keep; the other side is merged in.
        user_id: UUID of the acting administrator.

    Returns:
        Summary of the merge, including the surviving entity id and tier.

    Raises:
        DuplicateServiceError: If the candidate is resolved, the primary is not
            part of the pair, or the merge fails.
    """
    if candidate.status != DUPLICATE_STATUS_PENDING:
        raise DuplicateServiceError(f"Candidate {candidate.id} is already resolved (status={candidate.status})")
    if primary_entity_id not in (candidate.source_id, candidate.target_id):
        raise DuplicateServiceError(f"Entity {primary_entity_id} is not part of candidate {candidate.id}")

    secondary_id = candidate.target_id if primary_entity_id == candidate.source_id else candidate.source_id

    if candidate.entity_tier == TIER_WORK:
        primary = db.session.get(Work, primary_entity_id)
        secondary = db.session.get(Work, secondary_id)
        if primary is None or secondary is None:
            raise DuplicateServiceError("One of the Works no longer exists; the merge was aborted")
        surviving = merge_work(secondary, primary, user_id)
    elif candidate.entity_tier == TIER_EXPRESSION:
        primary = db.session.get(Expression, primary_entity_id)
        secondary = db.session.get(Expression, secondary_id)
        if primary is None or secondary is None:
            raise DuplicateServiceError("One of the Expressions no longer exists; the merge was aborted")
        surviving = merge_expression(secondary, primary, user_id)
    elif candidate.entity_tier == TIER_MANIFESTATION:
        primary = db.session.get(Manifestation, primary_entity_id)
        secondary = db.session.get(Manifestation, secondary_id)
        if primary is None or secondary is None:
            raise DuplicateServiceError("One of the Manifestations no longer exists; the merge was aborted")
        surviving = merge_manifestation(secondary, primary, user_id)
    else:
        raise DuplicateServiceError(f"Unsupported entity tier: {candidate.entity_tier!r}")

    candidate.status = DUPLICATE_STATUS_MERGED
    candidate.resolved_at = datetime.now(UTC)
    candidate.resolved_by_id = user_id
    db.session.add(candidate)
    db.session.commit()

    return {
        "candidate_id": candidate.id,
        "entity_tier": candidate.entity_tier,
        "primary_id": surviving.id,
        "merged_id": secondary_id,
    }


# ---------------------------------------------------------------------------
# API serialization
# ---------------------------------------------------------------------------


def _entity_payload(tier: str, entity_id: int) -> dict[str, Any] | None:
    """Serialize one side of a candidate for the review UI.

    Args:
        tier: One of ``"work"``, ``"expression"``, or ``"manifestation"``.
        entity_id: Primary key of the entity.

    Returns:
        Entity summary, or ``None`` when the entity has been removed.
    """
    return _describe_for_tier(tier, entity_id)


def serialize_candidate(candidate: DuplicateCandidate) -> dict[str, Any]:
    """Serialize a candidate together with both sides' entity metadata.

    Args:
        candidate: Candidate to serialize.

    Returns:
        JSON-serializable payload for the administrative review queue.
    """
    payload = candidate.to_dict()
    # The review UI must not present a classifier verdict and a model verdict
    # alike: a heuristic ``confidence`` of ``None`` is a categorical match, not a
    # missing value, and the badge is labelled from this field.
    payload["resolution_source"] = candidate.resolution_source
    payload["source"] = _entity_payload(candidate.entity_tier, candidate.source_id)
    payload["target"] = _entity_payload(candidate.entity_tier, candidate.target_id)
    payload["resolved_by_email"] = None
    if candidate.resolved_by_id is not None:
        resolver: User | None = db.session.get(User, candidate.resolved_by_id)
        payload["resolved_by_email"] = resolver.email if resolver is not None else None
    return payload


def candidate_query(
    *,
    status: str | None = DUPLICATE_STATUS_PENDING,
    entity_tier: str | None = None,
    min_confidence: float | None = None,
    page: int = 1,
    limit: int = 25,
) -> tuple[list[DuplicateCandidate], int]:
    """Public alias for :func:`list_candidates` used by the API layer."""
    return list_candidates(
        status=status,
        entity_tier=entity_tier,
        min_confidence=min_confidence,
        page=page,
        limit=limit,
    )
