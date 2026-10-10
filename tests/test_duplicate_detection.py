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
"""End-to-end tests for FRBR duplicate detection and merge.

Covers the complete lifecycle: model invariants, heuristic screening, local
LLM evaluation against a mocked Ollama, both FRBR merges, transactional
rollback, and the administrative REST API from listing through merge.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core import duplicate_service as svc
from app.core import frbr_merge
from app.db.models import (
    Contributor,
    DuplicateCandidate,
    EntityAuditLog,
    Expression,
    Item,
    Manifestation,
    SemanticLink,
    User,
    UserWorkIntent,
    Work,
    WorkContribution,
    db,
)

DUPLICATES_URL = "/api/v1/admin/duplicates"


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


@pytest.fixture
def read_only_metadata_headers(app):
    """Headers for a non-admin holding ``read:metadata`` but not ``write:metadata``.

    The shared ``custodian_headers`` fixture carries both metadata permissions,
    so a separate role is needed to prove the read/write split on the duplicate
    endpoints rather than merely that custodians are admitted.
    """
    from app.api.auth import generate_internal_jwt
    from app.db.models import Permission, Role, User

    with app.app_context():
        read_perm = Permission.query.filter_by(name="read:metadata").first()
        if not read_perm:
            read_perm = Permission(name="read:metadata")
            db.session.add(read_perm)

        role = Role(name="read_only_metadata_test")
        role.permissions.append(read_perm)
        db.session.add(role)

        user = User(email="read_only_metadata@iqoqo.local", display_name="Read Only")
        user.set_password("test-password")
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()

        return {"Authorization": f"Bearer {generate_internal_jwt(user)}"}


def make_work(title: str, *, authors: list[str] | None = None, year: int | None = None) -> Work:
    """Create and persist a Work with optional author metadata.

    Args:
        title: Work title.
        authors: Optional author display names stored in ``meta``.
        year: Optional first-publication year stored in ``meta``.

    Returns:
        The persisted Work.
    """
    meta: dict = {}
    if authors:
        meta["authors"] = authors
    if year:
        meta["year"] = year
    work = Work(title=title, sort_title=title.lower(), meta=meta)
    db.session.add(work)
    db.session.commit()
    return work


def make_expression(
    work: Work,
    *,
    language: str = "en",
    content_type: str = "text",
    label: str | None = None,
    meta: dict | None = None,
) -> Expression:
    """Create and persist an Expression belonging to a Work.

    Args:
        work: Parent Work.
        language: Expression language code.
        content_type: Expression content type.
        label: Optional Expression label/title stored in meta.
        meta: Optional additional metadata dict.

    Returns:
        The persisted Expression.
    """
    expr_meta = dict(meta or {})
    if label is not None:
        expr_meta["label"] = label
    expression = Expression(work_id=work.id, language=language, content_type=content_type, meta=expr_meta)
    db.session.add(expression)
    db.session.commit()
    return expression


def make_manifestation(expression: Expression, **kwargs) -> Manifestation:
    """Create and persist a Manifestation belonging to an Expression.

    Args:
        expression: Parent Expression.
        **kwargs: Column overrides such as ``isbn13`` or ``publisher``.

    Returns:
        The persisted Manifestation.
    """
    manifestation = Manifestation(expression_id=expression.id, meta={}, **kwargs)
    db.session.add(manifestation)
    db.session.commit()
    return manifestation


def make_user() -> User:
    """Create and persist a user so ownership foreign keys are satisfiable.

    A bare ``uuid4()`` satisfies ``Item.owner_id`` on SQLite, which does not
    enforce foreign keys, but PostgreSQL rejects it because no such user row
    exists.  Every id used in these tests must therefore be a real user.

    Returns:
        The persisted user.
    """
    user = User(email=f"dedupe-{uuid4().hex[:12]}@iqoqo.local", display_name="Dedupe Test")
    user.set_password("test-password")
    db.session.add(user)
    db.session.commit()
    return user


def enable_sqlite_foreign_keys() -> bool:
    """Enable SQLite FK enforcement so ``ON DELETE CASCADE`` behaves like PostgreSQL.

    No-op on PostgreSQL, which always enforces foreign keys and rejects the
    SQLite-only ``PRAGMA`` syntax.  Returns whether the pragma was issued.

    Returns:
        True when the pragma was applied.
    """
    if db.engine.dialect.name != "sqlite":
        return False
    db.session.execute(text("PRAGMA foreign_keys=ON"))
    return True


def make_item(manifestation: Manifestation, owner_id=None) -> Item:
    """Create and persist a physical Item belonging to a Manifestation.

    Args:
        manifestation: Parent Manifestation.
        owner_id: Owning user; a freshly persisted user is used when omitted.

    Returns:
        The persisted Item.
    """
    item = Item(manifestation_id=manifestation.id, owner_id=owner_id or make_user().id, condition="good", meta={})
    db.session.add(item)
    db.session.commit()
    return item


def llm_duplicate(confidence: float = 0.95) -> MagicMock:
    """Build a stubbed LLM verdict that reports a duplicate.

    Args:
        confidence: Confidence to report.

    Returns:
        A stand-in for :class:`DuplicateEvaluation`.
    """
    return MagicMock(verdict=True, confidence=confidence, reasoning="Same work, same edition.")


# ---------------------------------------------------------------------------
# 1. Model invariants
# ---------------------------------------------------------------------------


def test_candidate_rejects_reverse_duplicate_pair():
    """The unique constraint must be order-insensitive across the id pair."""
    source, target = make_work("Dune"), make_work("Dune")
    db.session.add(DuplicateCandidate(entity_tier="work", source_id=source.id, target_id=target.id, confidence=0.9, status="pending"))
    db.session.commit()

    db.session.add(DuplicateCandidate(entity_tier="work", source_id=target.id, target_id=source.id, confidence=0.8, status="pending"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_candidate_allows_same_ids_across_different_tiers():
    """Tier is part of the key: the same two ids may pair once per tier."""
    work, other_work = make_work("Neuromancer"), make_work("Neuromancer")
    expression = make_expression(work)
    manifestation = make_manifestation(expression)

    db.session.add(DuplicateCandidate(entity_tier="work", source_id=work.id, target_id=other_work.id, confidence=0.9, status="pending"))
    db.session.add(
        DuplicateCandidate(
            entity_tier="manifestation",
            source_id=manifestation.id,
            target_id=manifestation.id + 1,
            confidence=0.9,
            status="pending",
        )
    )
    db.session.commit()

    assert DuplicateCandidate.query.count() == 2


def test_candidate_is_re_exported_from_models_module():
    """``app.db.models`` is the public re-export surface used across the app."""
    from app.db import core, models

    assert models.DuplicateCandidate is core.DuplicateCandidate
    assert models.DUPLICATE_ENTITY_TIERS == ("work", "expression", "manifestation")
    assert models.DUPLICATE_CANDIDATE_STATUSES == ("pending", "merged", "dismissed")


# ---------------------------------------------------------------------------
# 2. Normalization and heuristic screening
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "left,right,expected_same",
    [
        ("The  Dispossessed", "the dispossessed", True),
        ("Dune", "Dune!", True),
        ("  Dune  ", "Dune", True),
        ("The Dispossessed", "The Dispossessed: An Ambiguous Utopia", False),
        ("Dune", "Neuromancer", False),
    ],
)
def test_normalize_title_collapses_bibliographic_noise(left, right, expected_same):
    """Case, padding, internal spacing, and trailing punctuation must not defeat blocking.

    A trailing subtitle is deliberately *not* collapsed: the service relies on
    fuzzy similarity and sort titles for those, not on lossy normalization.
    """
    assert (svc.normalize_title(left) == svc.normalize_title(right)) is expected_same


def test_title_similarity_catches_leading_article_variation():
    """Fuzzy similarity must bridge forms normalization alone cannot."""
    assert svc.title_similarity("The Hobbit", "Hobbit, The") > svc.TITLE_SIMILARITY_FLOOR


def test_title_similarity_is_bounded_and_empty_safe():
    """Similarity stays in 0.0-1.0 and returns 0.0 for unnormalizable input."""
    assert svc.title_similarity("Dune", "Dune") == 1.0
    assert svc.title_similarity("Dune", "Neuromancer") < 0.5
    assert svc.title_similarity(None, "Dune") == 0.0
    assert svc.title_similarity("", "") == 0.0


def test_work_creators_reads_authors_from_meta():
    """Author metadata is the primary creator source for a Work."""
    work = make_work("Dune", authors=["Frank Herbert"])
    assert svc.work_creators(work) == {"frank herbert"}


def test_screening_pairs_works_with_matching_titles():
    """An identical title corroborated by a shared author is queued with no model.

    This is the deterministic accept path: a categorical match, not a
    probability, so it neither consults the LLM nor needs a threshold.
    """
    make_work("The Left Hand of Darkness", authors=["Ursula K. Le Guin"])
    make_work("The Left Hand of Darkness", authors=["Ursula K. Le Guin"])
    make_work("A Wizard of Earthsea", authors=["Ursula K. Le Guin"])

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()) as mock_llm:
        report = svc.run_detection(tier="work", threshold=0.8)

    assert report.work_candidates == 1
    assert report.auto_accepted == 1
    assert mock_llm.call_count == 0
    assert report.created == 1
    # A classifier verdict carries no probability, so the column stays NULL.
    assert DuplicateCandidate.query.one().confidence is None
    assert DuplicateCandidate.query.one().resolution_source == "heuristic"


def test_screening_ignores_unrelated_titles():
    """Unrelated Works must not reach the LLM at all."""
    make_work("Dune", authors=["Frank Herbert"])
    make_work("Neuromancer", authors=["William Gibson"])

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()) as mock_llm:
        report = svc.run_detection(tier="work")

    assert report.candidate_pairs == 0
    assert mock_llm.call_count == 0
    assert report.created == 0


def test_screening_matches_manifestations_by_shared_ean():
    """A shared EAN is conclusive, so the pair is accepted without a model.

    ``isbn13`` is uniquely constrained, so it can never be shared between two
    Manifestations; the non-unique EAN/UPC/barcode family carries this signal.
    Previously this pair still paid for an LLM call despite the classifier
    already knowing the answer.
    """
    work = make_work("Dune", authors=["Frank Herbert"])
    expression = make_expression(work)
    make_manifestation(expression, ean="9780441013593", publisher="Ace")
    make_manifestation(expression, ean="9780441013593", publisher="Ace Books")

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()) as mock_llm:
        report = svc.run_detection(tier="manifestation")

    assert report.manifestation_candidates == 1
    assert report.auto_accepted == 1
    assert mock_llm.call_count == 0
    assert report.created == 1


def test_same_creator_different_volume_is_rejected_without_a_model():
    """Shared author plus a below-floor title is a rule, not an LLM decision.

    A parent Work and its sequel share an author and a title prefix, so they
    block on each other; the subtitle pushes title similarity to 0.69, just under
    the 0.72 floor.  This is the same-author noise the model used to filter.
    """
    make_work("The Lord of the Rings", authors=["J.R.R. Tolkien"])
    make_work("The Lord of the Rings: The Two Towers", authors=["J.R.R. Tolkien"])

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()) as mock_llm:
        report = svc.run_detection(tier="work")

    assert report.candidate_pairs == 1
    assert report.auto_rejected == 1
    assert report.created == 0
    assert mock_llm.call_count == 0
    assert DuplicateCandidate.query.count() == 0


def test_blocking_removes_unrelated_works_before_classification():
    """Unrelated titles share no blocking key, so they are never even paired.

    Documents why the LLM never saw cross-semantic cases: the blocking stage
    removes them first, which leaves the model adjudicating only pairs that
    already look lexically alike.
    """
    make_work("Neuromancer", authors=["William Gibson"])
    make_work("Snow Crash", authors=["William Gibson"])

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()) as mock_llm:
        report = svc.run_detection(tier="work")

    assert report.candidate_pairs == 0
    assert mock_llm.call_count == 0
    assert report.auto_rejected == 0


def test_grey_zone_is_left_undecided_by_the_heuristic_engine():
    """An identical title with conflicting creators is the genuine grey zone."""
    make_work("Emma", authors=["Jane Austen"])
    make_work("Emma", authors=["Anonymous"])

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()) as mock_llm:
        report = svc.run_detection(tier="work")

    assert report.candidate_pairs == 1
    assert report.needs_llm == 1
    assert report.created == 0
    assert mock_llm.call_count == 0


def test_llama_engine_adjudicates_the_grey_zone():
    """The same pair is settled when the operator opts into inference."""
    make_work("Emma", authors=["Jane Austen"])
    make_work("Emma", authors=["Anonymous"])

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()) as mock_llm:
        report = svc.run_detection(tier="work", engine="llama")

    assert report.needs_llm == 1
    assert mock_llm.call_count == 1
    assert report.created == 1
    assert DuplicateCandidate.query.one().resolution_source == "llama"
    assert DuplicateCandidate.query.one().confidence == 0.95


def test_heuristic_engine_needs_no_inference_service():
    """A scan must complete with Ollama unreachable under the default engine."""
    with patch.object(svc, "check_ollama_health", return_value=(False, "Ollama unreachable at http://x:1 (Error).")) as probe:
        make_work("Dune", authors=["Frank Herbert"])
        make_work("Dune", authors=["Frank Herbert"])
        report = svc.run_detection(tier="work")

    assert report.created == 1
    assert probe.call_count == 0


def test_run_detection_rejects_unknown_engine():
    """An unrecognized engine must be rejected, not silently downgraded."""
    with pytest.raises(svc.DuplicateServiceError):
        svc.run_detection(engine="gpt-9")


def test_isbn13_is_uniquely_constrained_so_it_can_never_be_a_shared_blocking_key():
    """A shared ISBN is impossible at the schema level, so only EAN/UPC/barcode can block on it.

    Two sibling Manifestations of the same Work still block on the inherited
    Work title, which is why this asserts the constraint rather than a zero
    candidate count.
    """
    work = make_work("Dune", authors=["Frank Herbert"])
    expression = make_expression(work)
    make_manifestation(expression, isbn13="9780441013593")

    with pytest.raises(IntegrityError):
        db.session.add(Manifestation(expression_id=expression.id, isbn13="9780441013593", meta={}))
        db.session.commit()
    db.session.rollback()


def test_dry_run_writes_nothing():
    """``dry_run`` must evaluate and report without persisting candidate rows."""
    make_work("Dune", authors=["Frank Herbert"])
    make_work("Dune", authors=["Frank Herbert"])

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()):
        report = svc.run_detection(tier="work", dry_run=True)

    assert report.candidate_pairs == 1
    # A dry run must never report a persisted row as created.
    assert report.would_create == 1
    assert report.created == 0
    assert DuplicateCandidate.query.count() == 0


def test_below_threshold_is_not_queued():
    """A low-confidence verdict must not create a review candidate.

    The pair shares a title but not a creator, so the classifier leaves it
    undecided and the ``llama`` engine is the one that applies the threshold.
    """
    make_work("Emma", authors=["Jane Austen"])
    make_work("Emma", authors=["Anonymous"])

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate(confidence=0.55)):
        report = svc.run_detection(tier="work", threshold=0.8, engine="llama")

    assert report.below_threshold == 1
    assert report.created == 0
    assert DuplicateCandidate.query.count() == 0


def test_expression_screening_no_parent_work_fallback_different_languages():
    """Two Expressions of one Work in different languages must not produce candidate pairs.

    Expression blocking keys derive strictly from normalize_title(expression.label)
    plus (language, content_type) without falling back to the parent Work title.
    """
    work = make_work("The Hobbit", authors=["J. R. R. Tolkien"])
    make_expression(work, language="en", content_type="text")
    make_expression(work, language="pl", content_type="text")

    report = svc.run_detection(tier="expression")
    assert report.candidate_pairs == 0
    assert report.created == 0


def test_expression_screening_cross_content_type_discarded():
    """Expressions differing in language or content_type must be discarded before scoring."""
    work = make_work("The Lord of the Rings", authors=["J. R. R. Tolkien"])
    e1 = Expression(work_id=work.id, language="en", content_type="text", meta={"label": "Fellowship"})
    e2 = Expression(work_id=work.id, language="en", content_type="sound", meta={"label": "Fellowship"})
    db.session.add_all([e1, e2])
    db.session.commit()

    report = svc.run_detection(tier="expression")
    assert report.candidate_pairs == 0
    assert report.created == 0


def test_expression_screening_positive_auto_accept():
    """Two Expressions sharing language, content_type, and normalized label are auto accepted."""
    work = make_work("The Hobbit", authors=["J. R. R. Tolkien"])
    e1 = Expression(work_id=work.id, language="en", content_type="text", meta={"label": "Original Text"})
    e2 = Expression(work_id=work.id, language="en", content_type="text", meta={"label": "Original Text"})
    db.session.add_all([e1, e2])
    db.session.commit()

    with patch.object(svc, "evaluate_pair_with_llm") as mock_llm:
        report = svc.run_detection(tier="expression")

    assert report.candidate_pairs == 1
    assert report.auto_accepted == 1
    assert report.created == 1
    assert mock_llm.call_count == 0


def test_describe_expression_payload_shape():
    """_describe_expression returns discriminated payload with required fields."""
    work = make_work("1984", authors=["George Orwell"])
    expr = Expression(work_id=work.id, language="en", content_type="text", meta={"label": "English Novel"})
    db.session.add(expr)
    db.session.commit()
    make_manifestation(expr)

    payload = svc._describe_for_tier("expression", expr.id)
    assert payload is not None
    assert payload["tier"] == "expression"
    assert payload["id"] == expr.id
    assert payload["label"] == "English Novel"
    assert payload["language"] == "en"
    assert payload["content_type"] == "text"
    assert payload["manifestation_count"] == 1
    assert "george orwell" in payload["creators"]


def test_dismissed_pairs_are_never_requeued():
    """A dismissed false positive must stay dismissed across later runs."""
    source, target = make_work("Dune", authors=["Frank Herbert"]), make_work("Dune", authors=["Frank Herbert"])
    svc.record_candidate("work", source.id, target.id, 0.9, "Previously dismissed")
    candidate = svc.find_existing_pair("work", source.id, target.id)
    svc.dismiss_candidate(candidate, user_id=None)

    with patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()) as mock_llm:
        report = svc.run_detection(tier="work")

    assert report.already_known == 1
    assert mock_llm.call_count == 0
    assert DuplicateCandidate.query.count() == 1


def test_run_detection_rejects_invalid_arguments():
    """Threshold and limit validation must fail fast with a service error."""
    with pytest.raises(svc.DuplicateServiceError):
        svc.run_detection(threshold=1.5)
    with pytest.raises(svc.DuplicateServiceError):
        svc.run_detection(limit=0)
    with pytest.raises(svc.DuplicateServiceError):
        svc.run_detection(tier="item")


# ---------------------------------------------------------------------------
# 3. Local LLM client
# ---------------------------------------------------------------------------


def test_parse_evaluation_extracts_confidence_and_rationale():
    """A well-formed JSON payload becomes a usable verdict."""
    verdict = svc.parse_evaluation('{"verdict": true, "confidence": 0.92, "reasoning": "Same edition."}')
    assert verdict.verdict is True
    assert verdict.confidence == 0.92
    assert verdict.reasoning == "Same edition."


@pytest.mark.parametrize("content", ["", "not json at all", '{"verdict": true}', '{"confidence": 2.0}'])
def test_parse_evaluation_rejects_malformed_payloads(content):
    """Malformed or out-of-range payloads must raise rather than be guessed at."""
    with pytest.raises(svc.DuplicateEvaluationError):
        svc.parse_evaluation(content)


def test_evaluate_pair_calls_ollama_chat_with_json_format():
    """The client posts to the local chat endpoint with structured output enabled."""
    response = MagicMock(status_code=200)
    response.json.return_value = {"message": {"content": '{"verdict": true, "confidence": 0.88, "reasoning": "Same work."}'}}
    left = {"title": "Dune", "creators": ["frank herbert"]}
    right = {"title": "Dune", "creators": ["frank herbert"]}

    with patch("app.core.duplicate_service.requests.post", return_value=response) as mock_post:
        verdict = svc.evaluate_pair_with_llm("work", left, right)

    assert verdict.confidence == 0.88
    _, kwargs = mock_post.call_args
    assert kwargs["json"]["format"] == "json"
    assert kwargs["json"]["stream"] is False
    assert kwargs["timeout"] == svc.OLLAMA_TIMEOUT_SECONDS


def test_evaluate_pair_raises_on_ollama_error():
    """A transport failure must surface as a typed service error."""
    with patch("app.core.duplicate_service.requests.post", side_effect=svc.requests.exceptions.ConnectionError("down")):
        with pytest.raises(svc.DuplicateEvaluationError):
            svc.evaluate_pair_with_llm("work", {"title": "Dune"}, {"title": "Dune"})


def test_llm_failure_is_recorded_and_skipped_not_raised():
    """An offline LLM must never abort a whole detection run."""
    make_work("Emma", authors=["Jane Austen"])
    make_work("Emma", authors=["Anonymous"])

    with patch("app.core.duplicate_service.requests.post", side_effect=svc.requests.exceptions.ConnectionError("down")):
        report = svc.run_detection(tier="work", engine="llama")

    assert report.llm_failures == 1
    assert report.created == 0


def test_check_ollama_health_reports_missing_model():
    """A reachable Ollama without the configured model is not healthy."""
    response = MagicMock(status_code=200)
    response.json.return_value = {"models": [{"name": "mistral:latest"}]}

    with patch("app.core.duplicate_service.requests.get", return_value=response):
        healthy, message = svc.check_ollama_health()

    assert healthy is False
    assert svc.ollama_model() in message


def test_check_ollama_health_accepts_present_model():
    """A reachable Ollama serving the configured model is healthy."""
    response = MagicMock(status_code=200)
    response.json.return_value = {"models": [{"name": svc.ollama_model()}]}

    with patch("app.core.duplicate_service.requests.get", return_value=response):
        assert svc.check_ollama_health()[0] is True


def test_ollama_model_honours_env_override(monkeypatch):
    """The dedupe model is configurable so a smaller local model can be used."""
    monkeypatch.setenv("OLLAMA_DEDUPE_MODEL", "qwen2.5:7b")
    assert svc.ollama_model() == "qwen2.5:7b"


# ---------------------------------------------------------------------------
# 4. Work merge
# ---------------------------------------------------------------------------


def test_merge_work_reparents_expressions_and_removes_source():
    """The surviving Work must adopt every Expression and absorb the source."""
    target = make_work("Dune", authors=["Frank Herbert"], year=1965)
    source = make_work("Dune", authors=["Frank Herbert"], year=1965)
    kept_expression = make_expression(target)
    moved_expression = make_expression(source)

    svc.merge_work(source, target, user_id=None)

    db.session.expire_all()
    assert db.session.get(Work, source.id) is None
    assert db.session.get(Work, target.id) is not None
    assert [e.id for e in db.session.get(Work, target.id).expressions] == sorted([kept_expression.id, moved_expression.id])


def test_merge_work_consolidates_contributions_without_duplicates():
    """Contributor rows are reconciled, not blindly duplicated."""
    target, source = make_work("Dune"), make_work("Dune")
    contributor = Contributor(name="Frank Herbert", type="person")
    db.session.add(contributor)
    db.session.commit()

    for work in (target, source):
        db.session.add(WorkContribution(work_id=work.id, contributor_id=contributor.id, role="author", sequence=0))
    db.session.commit()

    svc.merge_work(source, target, user_id=None)
    db.session.expire_all()

    remaining = WorkContribution.query.filter_by(contributor_id=contributor.id).all()
    assert len(remaining) == 1
    assert remaining[0].work_id == target.id


def test_merge_work_moves_user_content_and_audit_logs_the_merge():
    """User data must survive the consolidation, and the merge must be audited."""
    user_id = make_user().id
    target, source = make_work("Dune"), make_work("Dune")
    link = SemanticLink(
        entity_type="work",
        entity_id=source.id,
        authority="wikidata",
        external_uri="http://www.wikidata.org/Q1",
    )
    db.session.add(link)
    db.session.commit()

    svc.merge_work(source, target, user_id=user_id)

    moved = db.session.execute(select(SemanticLink).where(SemanticLink.authority == "wikidata")).scalar_one()
    assert moved.entity_id == target.id
    assert moved.external_uri == "http://www.wikidata.org/Q1"

    audit = EntityAuditLog.query.filter_by(change_type="merge_work").all()
    assert len(audit) == 1
    assert audit[0].entity_type == "work"
    # The entry identifies the removed row and names the survivor in the diff.
    assert audit[0].entity_id == source.id
    assert audit[0].diff["target_id"] == target.id
    assert audit[0].actor_id == user_id


def test_merge_work_preserves_wishlist_entries(app):
    """UserWorkIntent.work_id is ON DELETE CASCADE, so it must be re-pointed.

    Regression: merge_work re-pointed every referencing table except the
    wishlist, so merging a Work a user had on their list silently destroyed the
    entry on PostgreSQL.  Verified with SQLite foreign keys enforced.
    """
    target = make_work("Dune")
    source = make_work("Dune")
    user = User(email="wishlist-owner@iqoqo.local", display_name="Reader")
    user.set_password("x")
    db.session.add(user)
    db.session.commit()
    wishlist = UserWorkIntent(user_id=user.id, work_id=source.id, status="want_to_read")
    db.session.add(wishlist)
    db.session.commit()
    wishlist_id, target_id, source_id = wishlist.id, target.id, source.id

    # SQLite ignores foreign keys unless asked; PostgreSQL always enforces them.
    pragma = enable_sqlite_foreign_keys()
    try:
        svc.merge_work(source, target, user_id=None)
    finally:
        if pragma:
            db.session.execute(text("PRAGMA foreign_keys=OFF"))
    db.session.expire_all()

    moved = db.session.get(UserWorkIntent, wishlist_id)
    assert moved is not None, "the wishlist entry was cascade-deleted with the source Work"
    assert moved.work_id == target_id
    assert db.session.get(Work, source_id) is None


def test_merge_work_collapses_duplicate_wishlist_entries():
    """Two wishlist rows that become identical after the merge collapse to one."""
    target = make_work("Dune")
    source = make_work("Dune")
    user = User(email="double-wish@iqoqo.local", display_name="Reader")
    user.set_password("x")
    db.session.add(user)
    db.session.commit()
    db.session.add_all(
        [
            UserWorkIntent(user_id=user.id, work_id=source.id, status="want_to_read"),
            UserWorkIntent(user_id=user.id, work_id=target.id, status="want_to_read"),
        ]
    )
    db.session.commit()
    target_id = target.id

    svc.merge_work(source, target, user_id=None)

    rows = db.session.execute(select(UserWorkIntent).where(UserWorkIntent.user_id == user.id)).scalars().all()
    # The unique constraint (user_id, work_id, expression_id, manifestation_id)
    # would reject a second row, so the duplicate is dropped rather than kept.
    assert len(rows) == 1
    assert rows[0].work_id == target_id


def test_merge_work_handles_box_set_container(app):
    """WorkPart has a composite primary key and no surrogate id.

    Regression: the re-point helper selected ``model.id`` to detect a natural-key
    collision, which raised AttributeError for WorkPart and failed the entire
    merge for any Work involved in a box set or anthology (F15).
    """
    from app.db.contributions import WorkPart

    container = make_work("The Complete Anthology")
    member = make_work("Short Story I")
    source = make_work("The Complete Anthology")
    db.session.add(WorkPart(container_work_id=source.id, part_work_id=member.id, sequence=0))
    db.session.commit()
    target_id, source_id, member_id = container.id, source.id, member.id

    pragma = enable_sqlite_foreign_keys()
    try:
        svc.merge_work(source, container, user_id=None)
    finally:
        if pragma:
            db.session.execute(text("PRAGMA foreign_keys=OFF"))
    db.session.expire_all()

    reparented = db.session.get(WorkPart, {"container_work_id": target_id, "part_work_id": member_id})
    assert reparented is not None, "the box-set part row was lost"
    assert db.session.get(Work, source_id) is None


def test_merge_work_deduplicates_box_set_parts():
    """Merging two containers holding the same part keeps one row, not two."""
    from app.db.contributions import WorkPart

    target = make_work("Box A")
    source = make_work("Box B")
    member = make_work("Shared Story")
    db.session.add_all(
        [
            WorkPart(container_work_id=source.id, part_work_id=member.id, sequence=0),
            WorkPart(container_work_id=target.id, part_work_id=member.id, sequence=0),
        ]
    )
    db.session.commit()
    target_id, member_id = target.id, member.id

    svc.merge_work(source, target, user_id=None)

    rows = db.session.execute(select(WorkPart).where(WorkPart.container_work_id == target_id)).scalars().all()
    assert len(rows) == 1
    assert rows[0].part_work_id == member_id


def test_merge_work_rolls_back_completely_on_failure():
    """A mid-merge failure must leave both Works and all children untouched."""
    target = make_work("Dune")
    source = make_work("Dune")
    expression = make_expression(source)
    target_id, source_id = target.id, source.id

    with patch.object(frbr_merge, "repoint_references", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            svc.merge_work(source, target, user_id=None)
        db.session.rollback()

    db.session.expire_all()
    assert db.session.get(Work, source_id) is not None
    assert db.session.get(Work, target_id) is not None
    assert db.session.get(Expression, expression.id).work_id == source_id


def test_merge_work_rejects_self_merge():
    """Merging a Work into itself is a caller error, not a no-op."""
    work = make_work("Dune")
    with pytest.raises(svc.DuplicateServiceError):
        svc.merge_work(work, work, user_id=None)


# ---------------------------------------------------------------------------
# 5. Manifestation merge
# ---------------------------------------------------------------------------


def test_merge_manifestation_reparents_items():
    """Physical Items must follow the surviving Manifestation, not be cascaded away."""
    work = make_work("Dune")
    target = make_manifestation(make_expression(work), publisher="Ace")
    source = make_manifestation(make_expression(work), publisher="Ace Books")
    item = make_item(source)

    svc.merge_manifestation(source, target, user_id=None)
    db.session.expire_all()

    assert db.session.get(Manifestation, source.id) is None
    assert db.session.get(Item, item.id).manifestation_id == target.id


def test_merge_manifestation_adopts_missing_isbn_and_preserves_conflict_on_manifestation():
    """A missing ISBN is adopted; a conflicting one is preserved as an alternate."""
    work = make_work("Dune")
    target = make_manifestation(make_expression(work), isbn13="9780441013593")
    source = make_manifestation(make_expression(work), isbn13="9780441172719")

    svc.merge_manifestation(source, target, user_id=None)
    db.session.expire_all()

    surviving = db.session.get(Manifestation, target.id)
    assert surviving.isbn13 == "9780441013593"
    # The conflicting identifier is retained, but never promoted off the F3 tier.
    assert surviving.meta["alternate_isbn13"] == ["9780441172719"]
    assert db.session.get(Work, work.id).meta.get("isbn13") is None
    # The source row is gone, so the unique isbn13 index is left unambiguous.
    assert Manifestation.query.filter_by(isbn13="9780441172719").count() == 0


def test_merge_manifestation_adopts_isbn_absent_from_target():
    """When the primary has no ISBN, the source's is adopted outright."""
    work = make_work("Dune")
    target = make_manifestation(make_expression(work))
    source = make_manifestation(make_expression(work), isbn13="9780441013593")

    svc.merge_manifestation(source, target, user_id=None)
    db.session.expire_all()

    assert db.session.get(Manifestation, target.id).isbn13 == "9780441013593"


def test_merge_manifestation_rolls_back_completely_on_failure():
    """A mid-merge failure must leave both Manifestations and Items untouched."""
    work = make_work("Dune")
    target = make_manifestation(make_expression(work))
    source = make_manifestation(make_expression(work))
    item = make_item(source)
    target_id, source_id = target.id, source.id

    with patch.object(frbr_merge, "repoint_references", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            svc.merge_manifestation(source, target, user_id=None)
        db.session.rollback()

    db.session.expire_all()
    assert db.session.get(Manifestation, source_id) is not None
    assert db.session.get(Manifestation, target_id) is not None
    assert db.session.get(Item, item.id).manifestation_id == source_id


# ---------------------------------------------------------------------------
# 6. Candidate lifecycle
# ---------------------------------------------------------------------------


def test_resolve_candidate_merge_keeps_selected_primary():
    """The administrator's primary selection decides the survivor."""
    target = make_work("Dune", authors=["Frank Herbert"])
    source = make_work("Dune", authors=["Frank Herbert"])
    expression = make_expression(source)
    candidate = svc.record_candidate("work", source.id, target.id, 0.95, "Same work.")

    result = svc.resolve_candidate_merge(candidate, primary_entity_id=target.id, user_id=None)

    db.session.expire_all()
    assert result["primary_id"] == target.id
    assert result["merged_id"] == source.id
    assert db.session.get(Work, source.id) is None
    assert db.session.get(Expression, expression.id).work_id == target.id

    db.session.refresh(candidate)
    assert candidate.status == "merged"
    assert candidate.resolved_at is not None


def test_resolve_candidate_merge_rejects_foreign_primary():
    """A primary outside the pair is a client error, and nothing is merged."""
    left, right, other = make_work("Dune"), make_work("Dune"), make_work("Dune")
    candidate = svc.record_candidate("work", left.id, right.id, 0.95, "Same work.")

    with pytest.raises(svc.DuplicateServiceError):
        svc.resolve_candidate_merge(candidate, primary_entity_id=other.id, user_id=None)
    db.session.rollback()

    assert db.session.get(Work, left.id) is not None
    assert db.session.get(Work, right.id) is not None


def test_resolved_candidate_cannot_be_merged_or_dismissed_twice():
    """Lifecycle transitions are one-way; replaying a resolution must fail."""
    left, right = make_work("Dune"), make_work("Dune")
    candidate = svc.record_candidate("work", left.id, right.id, 0.95, "Same work.")
    svc.resolve_candidate_merge(candidate, primary_entity_id=left.id, user_id=None)

    with pytest.raises(svc.DuplicateServiceError):
        svc.resolve_candidate_merge(candidate, primary_entity_id=right.id, user_id=None)
    db.session.rollback()
    with pytest.raises(svc.DuplicateServiceError):
        svc.dismiss_candidate(candidate, user_id=None)
    db.session.rollback()


def test_list_candidates_filters_and_paginates():
    """Filtering and paging must happen in SQL and report an accurate total."""
    for index in range(5):
        left = make_work(f"Work {index}")
        right = make_work(f"Work {index}")
        svc.record_candidate("work", left.id, right.id, 0.5 + index / 10, "Reasoning")

    pending, total = svc.list_candidates(status="pending", min_confidence=0.8)
    assert total == 2
    assert len(pending) == 2
    assert all(candidate.confidence >= 0.8 for candidate in pending)

    first_page, total = svc.list_candidates(page=1, limit=2)
    second_page, _ = svc.list_candidates(page=2, limit=2)
    assert total == 5
    assert {c.id for c in first_page}.isdisjoint({c.id for c in second_page})


def test_list_candidates_rejects_unknown_filter_values():
    """An unrecognized filter must be rejected, not silently ignored."""
    with pytest.raises(svc.DuplicateServiceError):
        svc.list_candidates(status="archived")
    with pytest.raises(svc.DuplicateServiceError):
        svc.list_candidates(entity_tier="item")


def test_serialize_candidate_includes_both_sides():
    """The review payload must carry enough of each side to compare them."""
    left, right = make_work("Dune", authors=["Frank Herbert"]), make_work("Dune", authors=["Frank Herbert"])
    candidate = svc.record_candidate("work", left.id, right.id, 0.9, "Same work.")

    payload = svc.serialize_candidate(candidate)

    assert payload["source"]["id"] == left.id
    assert payload["target"]["id"] == right.id
    assert payload["source"]["creators"] == ["frank herbert"]
    assert payload["source"]["tier"] == "work"


# ---------------------------------------------------------------------------
# 7. Administrative REST API
# ---------------------------------------------------------------------------


def test_api_requires_authentication(client, admin_headers):
    """Anonymous callers must not reach the duplicate endpoints."""
    assert client.get(DUPLICATES_URL).status_code == 401
    assert client.post(f"{DUPLICATES_URL}/1/dismiss").status_code == 401
    assert client.post(f"{DUPLICATES_URL}/scan").status_code == 401


def test_user_without_metadata_permissions_cannot_reach_duplicate_endpoints(client, normal_user_headers):
    """A plain user holding neither metadata permission is refused everywhere.

    Duplicate review is a custodian surface, so the bar is ``read:metadata`` to
    list and ``write:metadata`` to mutate -- not merely being authenticated.
    """
    assert client.get(DUPLICATES_URL, headers=normal_user_headers).status_code == 403
    assert client.post(f"{DUPLICATES_URL}/scan", headers=normal_user_headers).status_code == 403
    assert client.post(f"{DUPLICATES_URL}/1/dismiss", headers=normal_user_headers).status_code == 403
    assert client.post(f"{DUPLICATES_URL}/1/merge", headers=normal_user_headers, json={"primary_id": 1}).status_code == 403


def test_custodian_can_list_candidates(client, custodian_headers):
    """A non-admin custodian holding read:metadata can read the review queue."""
    make_work("Dune", authors=["Frank Herbert"])
    make_work("Dune", authors=["Frank Herbert"])
    candidate = svc.record_candidate("work", 1, 2, 0.9, "Same work.")

    response = client.get(DUPLICATES_URL, headers=custodian_headers)

    assert response.status_code == 200
    assert response.get_json()["data"][0]["id"] == candidate.id


def test_custodian_can_trigger_scan(client, custodian_headers):
    """Scanning is a curator action, so a custodian with write:metadata may run it."""
    make_work("Dune", authors=["Frank Herbert"])
    make_work("Dune", authors=["Frank Herbert"])

    with (
        patch.object(svc, "check_ollama_health", return_value=(True, "ok")),
        patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()),
    ):
        response = client.post(f"{DUPLICATES_URL}/scan", headers=custodian_headers, json={"tier": "work"})

    assert response.status_code == 200
    assert response.get_json()["data"]["created"] == 1


def test_custodian_can_dismiss_candidate(client, custodian_headers):
    """Dismissing a false positive is a curator decision, not an admin-only one."""
    left, right = make_work("Dune", authors=["Frank Herbert"]), make_work("Dune", authors=["Frank Herbert"])
    candidate = svc.record_candidate("work", left.id, right.id, 0.9, "Same work.")

    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/dismiss", headers=custodian_headers)

    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "dismissed"
    # The deciding custodian is surfaced to the API.
    assert response.get_json()["data"]["resolved_by_email"] == "custodian_test@iqoqo.local"


def test_custodian_can_merge_candidate(client, custodian_headers):
    """A custodian with write:metadata may perform the merge, not just view it."""
    target = make_work("The Dispossessed", authors=["Ursula K. Le Guin"])
    source = make_work("The Dispossessed", authors=["Ursula K. Le Guin"])
    make_expression(target)
    make_expression(source)
    candidate = svc.record_candidate("work", source.id, target.id, 0.95, "Same work.")

    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=custodian_headers, json={"primary_id": target.id})

    assert response.status_code == 200
    assert response.get_json()["data"]["entity_tier"] == "work"
    assert response.get_json()["data"]["primary_id"] == target.id
    assert response.get_json()["data"]["merged_id"] == source.id
    assert db.session.get(Work, source.id) is None


def test_read_only_metadata_user_can_list_but_not_mutate(client, read_only_metadata_headers):
    """The read/write split: read:metadata lists the queue, write:metadata acts on it."""
    left, right = make_work("Dune", authors=["Frank Herbert"]), make_work("Dune", authors=["Frank Herbert"])
    candidate = svc.record_candidate("work", left.id, right.id, 0.9, "Same work.")

    assert client.get(DUPLICATES_URL, headers=read_only_metadata_headers).status_code == 200
    assert client.post(f"{DUPLICATES_URL}/scan", headers=read_only_metadata_headers).status_code == 403
    assert client.post(f"{DUPLICATES_URL}/{candidate.id}/dismiss", headers=read_only_metadata_headers).status_code == 403
    assert (
        client.post(
            f"{DUPLICATES_URL}/{candidate.id}/merge",
            headers=read_only_metadata_headers,
            json={"primary_id": candidate.target_id},
        ).status_code
        == 403
    )


def test_api_lists_pending_candidates(client, admin_headers):
    """The queue defaults to pending candidates and reports a total."""
    left, right = make_work("Dune", authors=["Frank Herbert"]), make_work("Dune", authors=["Frank Herbert"])
    svc.record_candidate("work", left.id, right.id, 0.93, "Same work.")

    response = client.get(DUPLICATES_URL, headers=admin_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["meta"]["total"] == 1
    assert body["data"][0]["source"]["title"] == "Dune"
    assert body["data"][0]["target"]["creators"] == ["frank herbert"]


def test_api_rejects_unknown_status_filter(client, admin_headers):
    """An out-of-vocabulary filter returns 400 rather than an empty page."""
    response = client.get(f"{DUPLICATES_URL}?status=archived", headers=admin_headers)
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_api_dismiss_candidate(client, admin_headers):
    """Dismissing marks the candidate and records the deciding admin."""
    left, right = make_work("Dune"), make_work("Dune")
    candidate = svc.record_candidate("work", left.id, right.id, 0.9, "Same work.")

    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/dismiss", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "dismissed"

    db.session.refresh(candidate)
    assert candidate.status == "dismissed"
    assert candidate.resolved_by_id is not None
    # The deciding admin is surfaced to the API, not stored as a column.
    assert response.get_json()["data"]["resolved_by_email"] == "test_admin@iqoqo.local"


def test_api_dismiss_twice_conflicts(client, admin_headers):
    """Re-dismissing a resolved candidate is a conflict, not a silent success."""
    left, right = make_work("Dune"), make_work("Dune")
    candidate = svc.record_candidate("work", left.id, right.id, 0.9, "Same work.")
    client.post(f"{DUPLICATES_URL}/{candidate.id}/dismiss", headers=admin_headers)

    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/dismiss", headers=admin_headers)
    assert response.status_code == 409


def test_api_missing_candidate_returns_404(client, admin_headers):
    """Unknown candidate ids are 404 for both dismiss and merge."""
    assert client.post(f"{DUPLICATES_URL}/999999/dismiss", headers=admin_headers).status_code == 404
    assert client.post(f"{DUPLICATES_URL}/999999/merge", headers=admin_headers, json={"primary_id": 1}).status_code == 404


def test_api_merge_requires_integer_primary(client, admin_headers):
    """A missing or non-integer primary_id is a client error."""
    left, right = make_work("Dune"), make_work("Dune")
    candidate = svc.record_candidate("work", left.id, right.id, 0.9, "Same work.")

    assert client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=admin_headers, json={}).status_code == 400
    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=admin_headers, json={"primary_id": "abc"})
    assert response.status_code == 400
    # A boolean is an int in Python; it must still be rejected.
    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=admin_headers, json={"primary_id": True})
    assert response.status_code == 400


def test_api_merge_rejects_foreign_primary(client, admin_headers):
    """A primary outside the pair is rejected and both Works survive."""
    left, right, other = make_work("Dune"), make_work("Dune"), make_work("Dune")
    candidate = svc.record_candidate("work", left.id, right.id, 0.9, "Same work.")

    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=admin_headers, json={"primary_id": other.id})
    assert response.status_code == 400
    assert db.session.get(Work, left.id) is not None
    assert db.session.get(Work, right.id) is not None


def test_api_merge_executes_and_rolls_back_on_failure(client, admin_headers):
    """A successful merge consolidates; a failing one leaves both sides intact."""
    target = make_work("Dune", authors=["Frank Herbert"])
    source = make_work("Dune", authors=["Frank Herbert"])
    expression = make_expression(source)
    candidate = svc.record_candidate("work", source.id, target.id, 0.95, "Same work.")

    with patch.object(frbr_merge, "repoint_references", side_effect=RuntimeError("boom")):
        response = client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=admin_headers, json={"primary_id": target.id})
    assert response.status_code == 500
    assert response.get_json()["error"] == "Merge failed and was rolled back"

    db.session.expire_all()
    assert db.session.get(Work, source.id) is not None
    assert db.session.get(Expression, expression.id).work_id == source.id

    # The same candidate can still be merged successfully afterwards.
    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=admin_headers, json={"primary_id": target.id})
    assert response.status_code == 200
    db.session.expire_all()
    assert db.session.get(Work, source.id) is None
    assert db.session.get(Expression, expression.id).work_id == target.id


def test_api_scan_requires_healthy_ollama_only_for_the_llama_engine(client, admin_headers):
    """The Ollama probe is a prerequisite of the ``llama`` engine only.

    The default engine resolves candidates deterministically, so demanding a
    running model would make an ordinary offline scan impossible.
    """
    with patch.object(svc, "check_ollama_health", return_value=(False, "Ollama unreachable at http://x:1 (Error).")) as probe:
        response = client.post(f"{DUPLICATES_URL}/scan", headers=admin_headers, json={"tier": "work", "engine": "llama"})

    assert response.status_code == 409
    assert "ollama pull" in response.get_json()["error"]
    assert probe.call_count == 1

    make_work("Dune", authors=["Frank Herbert"])
    make_work("Dune", authors=["Frank Herbert"])
    with patch.object(svc, "check_ollama_health", return_value=(False, "Ollama unreachable at http://x:1 (Error).")) as probe:
        response = client.post(f"{DUPLICATES_URL}/scan", headers=admin_headers, json={"tier": "work"})

    assert response.status_code == 200
    assert probe.call_count == 0, "the default engine must not probe for an inference service"


def test_api_scan_rejects_unknown_engine(client, admin_headers):
    """An unrecognized engine must be a 400, not a silent fallback."""
    response = client.post(f"{DUPLICATES_URL}/scan", headers=admin_headers, json={"tier": "work", "engine": "gpt-9"})

    assert response.status_code == 400
    assert "engine" in response.get_json()["error"]


def test_api_scan_queues_candidates(client, admin_headers):
    """A healthy scan queues new candidates and returns run counters."""
    make_work("Dune", authors=["Frank Herbert"])
    make_work("Dune", authors=["Frank Herbert"])

    with (
        patch.object(svc, "check_ollama_health", return_value=(True, "ok")),
        patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate()),
    ):
        response = client.post(f"{DUPLICATES_URL}/scan", headers=admin_headers, json={"tier": "work"})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["created"] == 1
    assert data["work_candidates"] == 1

    queue = client.get(DUPLICATES_URL, headers=admin_headers).get_json()
    assert queue["meta"]["total"] == 1


def test_api_scan_rejects_bad_tier(client, admin_headers):
    """An unrecognized tier returns 400 rather than scanning nothing silently."""
    with patch.object(svc, "check_ollama_health", return_value=(True, "ok")):
        response = client.post(f"{DUPLICATES_URL}/scan", headers=admin_headers, json={"tier": "item"})

    assert response.status_code == 400


def test_api_full_lifecycle_from_detection_to_merge(client, admin_headers):
    """The end-to-end path on the default engine: detect, list, merge, verify.

    Identical title plus a shared author is a categorical match, so the pair is
    queued by the classifier with no model involved and no confidence attached.
    """
    target = make_work("The Dispossessed", authors=["Ursula K. Le Guin"], year=1974)
    source = make_work("The Dispossessed", authors=["Ursula K. Le Guin"], year=1974)
    target_expression = make_expression(target)
    source_expression = make_expression(source)
    source_item_work = make_expression(source)

    scan = client.post(f"{DUPLICATES_URL}/scan", headers=admin_headers, json={"tier": "work"})
    assert scan.get_json()["data"]["created"] == 1
    assert scan.get_json()["data"]["engine"] == "heuristic"

    queue = client.get(DUPLICATES_URL, headers=admin_headers).get_json()
    assert queue["meta"]["total"] == 1
    candidate = queue["data"][0]
    assert candidate["resolution_source"] == "heuristic"
    assert candidate["confidence"] is None
    assert "identical normalized title" in candidate["llm_reasoning"]

    merged = client.post(f"{DUPLICATES_URL}/{candidate['id']}/merge", headers=admin_headers, json={"primary_id": target.id})
    assert merged.status_code == 200
    assert merged.get_json()["data"]["primary_id"] == target.id

    db.session.expire_all()
    assert db.session.get(Work, source.id) is None
    for expression in (target_expression, source_expression, source_item_work):
        assert db.session.get(Expression, expression.id).work_id == target.id


def test_api_full_lifecycle_through_the_llama_engine(client, admin_headers):
    """The same path with inference opted in, including the confidence filter."""
    target = make_work("Dune", authors=["Frank Herbert"], year=1965)
    source = make_work("Dune", authors=["Frank Herbert"], year=1965)
    make_expression(target)
    make_expression(source)

    with (
        patch.object(svc, "check_ollama_health", return_value=(True, "ok")),
        patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate(0.97)),
    ):
        scan = client.post(f"{DUPLICATES_URL}/scan", headers=admin_headers, json={"tier": "work", "engine": "llama"})

    # The classifier short-circuits a categorical match, so opting into the LLM
    # engine still does not spend a call on it.
    assert scan.get_json()["data"]["created"] == 1
    assert scan.get_json()["data"]["llm_evaluations"] == 0

    queue = client.get(f"{DUPLICATES_URL}?min_confidence=0.9", headers=admin_headers).get_json()
    # A heuristic candidate has a NULL confidence, so the filter excludes it.
    assert queue["meta"]["total"] == 0

    grey_target = make_work("Emma", authors=["Anonymous"])
    grey_source = make_work("Emma", authors=["Someone Distinct"])
    make_expression(grey_target)
    make_expression(grey_source)
    with (
        patch.object(svc, "check_ollama_health", return_value=(True, "ok")),
        patch.object(svc, "evaluate_pair_with_llm", return_value=llm_duplicate(0.97)) as mock_llm,
    ):
        scan = client.post(f"{DUPLICATES_URL}/scan", headers=admin_headers, json={"tier": "work", "engine": "llama"})

    assert scan.get_json()["data"]["llm_evaluations"] >= 1
    assert mock_llm.call_count >= 1

    queue = client.get(f"{DUPLICATES_URL}?min_confidence=0.9", headers=admin_headers).get_json()
    llama_candidates = [c for c in queue["data"] if c["resolution_source"] == "llama"]
    assert llama_candidates, "expected at least one llama-sourced candidate above the confidence filter"
    assert llama_candidates[0]["confidence"] == 0.97
    assert llama_candidates[0]["llm_reasoning"].startswith("Same work, same edition.")

    merged = client.post(f"{DUPLICATES_URL}/{llama_candidates[0]['id']}/merge", headers=admin_headers, json={"primary_id": grey_target.id})
    assert merged.status_code == 200

    # The resolved candidate leaves the pending queue but remains auditable.
    assert client.get(DUPLICATES_URL, headers=admin_headers).get_json()["meta"]["total"] == 1
    history = client.get(f"{DUPLICATES_URL}?status=merged", headers=admin_headers).get_json()
    assert history["meta"]["total"] == 1
    assert history["data"][0]["resolved_by_email"] == "test_admin@iqoqo.local"

    db.session.expire_all()
    assert db.session.get(Work, grey_source.id) is None

    audit = EntityAuditLog.query.filter_by(change_type="merge_work").all()
    assert len(audit) == 1
    assert audit[0].diff["source_id"] == grey_source.id
    assert audit[0].diff["target_id"] == grey_target.id


# ---------------------------------------------------------------------------
# 8. Cascade regressions
# ---------------------------------------------------------------------------


def test_merge_work_does_not_cascade_delete_reparented_expressions():
    """Regression: ``Work.expressions`` is ``delete-orphan``, so an ORM delete
    of the source would destroy the Expressions the merge just re-parented."""
    target, source = make_work("Dune"), make_work("Dune")
    expressions = [make_expression(source), make_expression(source), make_expression(source)]

    svc.merge_work(source, target, user_id=None)
    db.session.expire_all()

    for expression in expressions:
        surviving = db.session.get(Expression, expression.id)
        assert surviving is not None, "merge cascade-deleted an Expression instead of re-parenting it"
        assert surviving.work_id == target.id


def test_merge_work_preserves_the_full_expression_subtree():
    """Regression: Manifestations and Items under a re-parented Expression must survive."""
    target, source = make_work("Dune"), make_work("Dune")
    expression = make_expression(source)
    manifestation = make_manifestation(expression)
    item = make_item(manifestation)

    svc.merge_work(source, target, user_id=None)
    db.session.expire_all()

    assert db.session.get(Expression, expression.id).work_id == target.id
    assert db.session.get(Manifestation, manifestation.id).expression_id == expression.id
    assert db.session.get(Item, item.id).manifestation_id == manifestation.id


def test_merge_manifestation_does_not_cascade_delete_reparented_items():
    """Regression: ``Manifestation.items`` is ``delete-orphan``, so an ORM delete
    of the source would destroy the physical Items the merge just re-parented."""
    work = make_work("Dune")
    target = make_manifestation(make_expression(work))
    source = make_manifestation(make_expression(work))
    items = [make_item(source), make_item(source), make_item(source)]

    svc.merge_manifestation(source, target, user_id=None)
    db.session.expire_all()

    for item in items:
        surviving = db.session.get(Item, item.id)
        assert surviving is not None, "merge cascade-deleted an Item instead of re-parenting it"
        assert surviving.manifestation_id == target.id


def test_merge_adopting_isbn_respects_the_unique_index():
    """Regression: adopting the source ISBN while the source row still held it
    violated the unique isbn13 index at flush time."""
    work = make_work("Dune")
    target = make_manifestation(make_expression(work))
    source = make_manifestation(make_expression(work), isbn13="9780441013593")

    svc.merge_manifestation(source, target, user_id=None)
    db.session.expire_all()

    assert db.session.get(Manifestation, target.id).isbn13 == "9780441013593"
    assert Manifestation.query.count() == 1


# ---------------------------------------------------------------------------
# Expression merge & candidate lifecycle
# ---------------------------------------------------------------------------


def test_merge_expression_reparents_manifestations_and_preserves_intent():
    """Child Manifestations and user wishlist rows follow the surviving Expression."""
    from app.db.core import UserWorkIntent

    work = make_work("Dune")
    target = make_expression(work, language="en", content_type="text", label="Original Text")
    source = make_expression(work, language="en", content_type="text", label="Duplicate Text")
    manif = make_manifestation(source)

    user = User(email="test_uwi_expr@iqoqo.local", password_hash="fake", visibility="private")
    db.session.add(user)
    db.session.commit()

    uwi = UserWorkIntent(user_id=user.id, work_id=work.id, expression_id=source.id, status="want_to_read")
    db.session.add(uwi)
    db.session.commit()

    target_id, source_id, manif_id, uwi_id = target.id, source.id, manif.id, uwi.id

    svc.merge_expression(source, target, user_id=None)
    db.session.expire_all()

    assert db.session.get(Expression, source_id) is None
    assert db.session.get(Manifestation, manif_id).expression_id == target_id
    assert db.session.get(UserWorkIntent, uwi_id).expression_id == target_id

    audit = EntityAuditLog.query.filter_by(entity_type="expression", change_type="merge_expression").first()
    assert audit is not None
    assert audit.diff["source_id"] == source_id
    assert audit.diff["target_id"] == target_id
    assert audit.diff["migrated_children"] == 1


def test_merge_expression_refuses_different_languages():
    """Distinct languages represent distinct intellectual realizations and must never merge."""
    work = make_work("Dune")
    target = make_expression(work, language="en", content_type="text")
    source = make_expression(work, language="pl", content_type="text")

    with pytest.raises(svc.DuplicateServiceError, match="different languages"):
        svc.merge_expression(source, target, user_id=None)


def test_merge_expression_refuses_different_content_types():
    """Distinct content types (e.g. text vs audio) must never merge."""
    work = make_work("Dune")
    target = make_expression(work, language="en", content_type="text")
    source = make_expression(work, language="en", content_type="sound")

    with pytest.raises(svc.DuplicateServiceError, match="different content types"):
        svc.merge_expression(source, target, user_id=None)


def test_merge_expression_rejects_self_merge():
    """Merging an Expression into itself is a caller error."""
    work = make_work("Dune")
    expr = make_expression(work, language="en", content_type="text")

    with pytest.raises(svc.DuplicateServiceError, match="Cannot merge an Expression with itself"):
        svc.merge_expression(expr, expr, user_id=None)


def test_resolve_candidate_merge_expression_tier():
    """Resolving an Expression candidate consolidates the pair and updates queue status."""
    work = make_work("Dune")
    target = make_expression(work, language="en", content_type="text", label="Dune Text")
    source = make_expression(work, language="en", content_type="text", label="Dune Text Duplicate")
    manif = make_manifestation(source)
    candidate = svc.record_candidate(
        "expression", source.id, target.id, 0.95, "Same expression.", resolution_source=svc.DUPLICATE_RESOLUTION_HEURISTIC
    )
    assert candidate is not None

    result = svc.resolve_candidate_merge(candidate, primary_entity_id=target.id, user_id=None)

    assert result["primary_id"] == target.id
    assert result["merged_id"] == source.id
    assert result["entity_tier"] == "expression"

    db.session.expire_all()
    assert db.session.get(Expression, source.id) is None
    assert db.session.get(Manifestation, manif.id).expression_id == target.id

    db.session.refresh(candidate)
    assert candidate.status == "merged"


def test_api_list_candidates_filters_by_entity_tier_expression(client, custodian_headers):
    """GET /duplicates?entity_tier=expression filters candidate queue to Expression tier."""
    w1, w2 = make_work("Work A"), make_work("Work B")
    c_work = svc.record_candidate("work", w1.id, w2.id, 0.9, "Work match")
    e1 = make_expression(w1, language="en", content_type="text")
    e2 = make_expression(w1, language="en", content_type="text")
    c_expr = svc.record_candidate("expression", e1.id, e2.id, 0.9, "Expr match")
    assert c_work is not None
    assert c_expr is not None

    response = client.get(f"{DUPLICATES_URL}?entity_tier=expression", headers=custodian_headers)

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == c_expr.id
    assert data[0]["entity_tier"] == "expression"


def test_api_scan_supports_expression_tier(client, custodian_headers):
    """POST /duplicates/scan admits tier='expression' without error."""
    work = make_work("Test Work for Expression Scan")
    make_expression(work, language="en", content_type="text", label="Shared Label")
    make_expression(work, language="en", content_type="text", label="Shared Label")

    response = client.post(f"{DUPLICATES_URL}/scan", headers=custodian_headers, json={"tier": "expression"})

    assert response.status_code == 200
    report_data = response.get_json()["data"]
    assert report_data["expression_candidates"] >= 1


def test_api_merge_expression_candidate_end_to_end(client, custodian_headers):
    """POST /duplicates/<id>/merge resolves an Expression candidate end-to-end."""
    work = make_work("The Hobbit")
    target = make_expression(work, language="en", content_type="text", label="The Hobbit (English)")
    source = make_expression(work, language="en", content_type="text", label="The Hobbit (English Duplicate)")
    manif = make_manifestation(source)
    candidate = svc.record_candidate("expression", source.id, target.id, 0.95, "Duplicate expression.")
    assert candidate is not None

    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=custodian_headers, json={"primary_id": target.id})

    assert response.status_code == 200
    body = response.get_json()
    assert body["data"]["entity_tier"] == "expression"
    assert body["data"]["primary_id"] == target.id
    assert body["data"]["merged_id"] == source.id

    db.session.expire_all()
    assert db.session.get(Expression, source.id) is None
    assert db.session.get(Manifestation, manif.id).expression_id == target.id


def test_api_merge_expression_refuses_cross_language_with_400(client, custodian_headers):
    """POST /duplicates/<id>/merge returns 400 when attempting a cross-language Expression merge."""
    work = make_work("The Hobbit")
    target = make_expression(work, language="en", content_type="text")
    source = make_expression(work, language="pl", content_type="text")
    candidate = svc.record_candidate("expression", source.id, target.id, 0.95, "Forced candidate.")
    assert candidate is not None

    response = client.post(f"{DUPLICATES_URL}/{candidate.id}/merge", headers=custodian_headers, json={"primary_id": target.id})

    assert response.status_code == 400
    assert "different languages" in response.get_json()["error"]
