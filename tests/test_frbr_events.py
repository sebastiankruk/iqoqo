"""Tests for FRBRoo event-based modeling (Section 2 of release-0-7-13).

Pins:

- Boundary integrity: creator → Work, performer → Expression, publisher → Manifestation.
- ``Expression.kind`` controlled vocabulary (``live_performance``) and the
  reversible migration that introduced it.
- Concert graph shape: Work → live-performance Expression → video/audio Manifestation.
- F16 Container Work aggregation check-constraint behavior for board games.
- API payload exposure of contributions and container aggregation contents.
"""

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

# pylint: disable=too-many-lines

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.frbr_service import (
    add_container_component,
    add_expression_contribution,
    add_manifestation_contribution,
    add_work_contribution,
    clear_expression_kind,
    create_expression,
    create_manifestation,
    create_work,
    get_or_create_contributor,
    get_or_create_live_performance_expression,
    get_or_create_rulebook_work,
    is_live_performance,
    serialize_container_aggregation,
    serialize_contributions,
    update_expression,
)
from app.core.ingest import _detect_live_performance
from app.db.audio import Contributor as AudioContributor
from app.db.audio import ExpressionContribution as AudioExpressionContribution
from app.db.audio import WorkContribution as AudioWorkContribution
from app.db.contributions import (
    Contributor,
    ExpressionContribution,
    ManifestationContribution,
    WorkContribution,
)
from app.db.core import EXPRESSION_KIND_LIVE_PERFORMANCE, EXPRESSION_KINDS, Expression, Manifestation, Work
from app.db.games import ContainerAggregation
from app.db.models import db
from app.db.video import ManifestationContribution as VideoManifestationContribution

# ---------------------------------------------------------------------------
# 2.1 — Shared event entities importable from both old and new paths
# ---------------------------------------------------------------------------


class TestSharedContributionEntities:
    """All strategies must import the *same* shared contribution models."""

    def test_audio_module_reexports_shared_models(self):
        assert AudioContributor is Contributor
        assert AudioWorkContribution is WorkContribution
        assert AudioExpressionContribution is ExpressionContribution

    def test_video_module_reexports_shared_models(self):
        assert VideoManifestationContribution is ManifestationContribution

    def test_models_shim_exposes_all_shared_events(self):
        from app.db.models import (  # noqa: F401
            Contributor,
            ExpressionContribution,
            ManifestationContribution,
            WorkContribution,
            WorkPart,
        )


# ---------------------------------------------------------------------------
# 2.6a — Boundary integrity: creator → Work, performer → Expression, publisher → Manifestation
# ---------------------------------------------------------------------------


class TestEventBoundaryIntegrity:
    def test_creator_lands_on_work_only(self, app):
        with app.app_context():
            work = create_work("Symphony No. 5")
            composer = get_or_create_contributor("Ludwig van Beethoven")
            wc = add_work_contribution(work.id, composer.id, "composer")

            assert wc.work_id == work.id
            assert wc.role == "composer"
            # Work.contributions exposed
            assert len(work.contributions) == 1
            # No Expression/Manifestation rows leaked
            assert ExpressionContribution.query.count() == 0
            assert ManifestationContribution.query.count() == 0

    def test_performer_lands_on_expression_only(self, app):
        with app.app_context():
            work = create_work("Kind of Blue")
            expr = create_expression(work.id, content_type="music")
            performer = get_or_create_contributor("Miles Davis")
            ec = add_expression_contribution(expr.id, performer.id, "performer")

            assert ec.expression_id == expr.id
            assert ec.role == "performer"
            assert len(expr.contributions) == 1
            assert WorkContribution.query.count() == 0
            assert ManifestationContribution.query.count() == 0

    def test_publisher_lands_on_manifestation_only(self, app):
        with app.app_context():
            work = create_work("A Movie")
            expr = create_expression(work.id, content_type="movie")
            manif = create_manifestation(expr.id, publisher="Warner Bros")
            studio = get_or_create_contributor("Warner Bros", contributor_type="organization")
            mc = add_manifestation_contribution(manif.id, studio.id, "studio")

            assert mc.manifestation_id == manif.id
            assert mc.role == "studio"
            assert WorkContribution.query.count() == 0
            assert ExpressionContribution.query.count() == 0


# ---------------------------------------------------------------------------
# 2.2 — Expression.kind controlled vocabulary
# ---------------------------------------------------------------------------


class TestExpressionKind:
    def test_default_kind_is_null(self, app):
        with app.app_context():
            work = create_work("Studio Album")
            expr = create_expression(work.id, content_type="music")
            assert expr.kind is None
            assert not is_live_performance(expr)

    def test_create_live_performance_expression(self, app):
        with app.app_context():
            work = create_work("Live at the BBC")
            expr = create_expression(work.id, content_type="music", kind=EXPRESSION_KIND_LIVE_PERFORMANCE)
            assert expr.kind == "live_performance"
            assert is_live_performance(expr)

    def test_invalid_kind_rejected_on_create(self, app):
        with app.app_context():
            work = create_work("X")
            with pytest.raises(ValueError, match="Invalid expression kind"):
                create_expression(work.id, kind="bogus_kind")

    def test_invalid_kind_rejected_on_update(self, app):
        with app.app_context():
            work = create_work("Y")
            expr = create_expression(work.id)
            with pytest.raises(ValueError, match="Invalid expression kind"):
                update_expression(expr.id, kind="not_a_kind")

    def test_update_and_clear_kind(self, app):
        with app.app_context():
            work = create_work("Z")
            expr = create_expression(work.id)
            update_expression(expr.id, kind="live_performance")
            assert db.session.get(Expression, expr.id).kind == "live_performance"

            clear_expression_kind(expr.id)
            assert db.session.get(Expression, expr.id).kind is None

    def test_vocabulary_is_pinned(self):
        # Adding new kinds is allowed but should be deliberate — pin the
        # current controlled vocabulary so any addition shows up in review.
        assert EXPRESSION_KINDS == ("live_performance",)


# ---------------------------------------------------------------------------
# 2.3 — Concert graph shape: Work → live-performance Expression → Manifestation
# ---------------------------------------------------------------------------


class TestConcertGraphShape:
    def test_live_performance_expression_with_performers(self, app):
        with app.app_context():
            work = create_work("Live in Tokyo")
            expr = get_or_create_live_performance_expression(
                work_id=work.id,
                content_type="movie",
                venue="Budokan",
                performance_date="1978-02-28",
                performers=[("Cheap Trick", "band")],
            )

            assert expr.kind == "live_performance"
            assert expr.content_type == "movie"
            assert expr.meta.get("venue") == "Budokan"
            assert expr.meta.get("performance_date") == "1978-02-28"

            # Performer created and linked via ExpressionContribution
            ecs = ExpressionContribution.query.filter_by(expression_id=expr.id).all()
            assert len(ecs) == 1
            assert ecs[0].role == "band"
            assert ecs[0].contributor.name == "Cheap Trick"

    def test_live_performance_idempotent_per_work_and_content_type(self, app):
        with app.app_context():
            work = create_work("Concert")
            expr1 = get_or_create_live_performance_expression(work_id=work.id, content_type="music")
            expr2 = get_or_create_live_performance_expression(work_id=work.id, content_type="music")
            assert expr1.id == expr2.id

            # Different content_type → different Expression (audio vs video of same concert)
            expr_video = get_or_create_live_performance_expression(work_id=work.id, content_type="movie")
            assert expr_video.id != expr1.id

    def test_live_performance_merges_venue_into_existing_meta(self, app):
        with app.app_context():
            work = create_work("Live")
            expr1 = get_or_create_live_performance_expression(work_id=work.id, content_type="music")
            assert (expr1.meta or {}).get("venue") is None

            expr2 = get_or_create_live_performance_expression(work_id=work.id, content_type="music", venue="Royal Albert Hall")
            assert expr2.id == expr1.id
            refreshed = db.session.get(Expression, expr1.id)
            assert refreshed.meta.get("venue") == "Royal Albert Hall"

    def test_concert_manifestation_links_to_live_expression(self, app):
        with app.app_context():
            work = create_work("MTV Unplugged in New York")
            expr = get_or_create_live_performance_expression(
                work_id=work.id,
                content_type="music",
                performers=[("Nirvana", "band")],
            )
            manif = create_manifestation(expr.id, publisher="Geffen")

            assert manif.expression.kind == "live_performance"
            assert manif.expression.work_id == work.id


# ---------------------------------------------------------------------------
# 2.3 — Live-performance detection helper
# ---------------------------------------------------------------------------


class TestDetectLivePerformance:
    @pytest.mark.parametrize(
        "meta",
        [
            {"genres": ["Rock", "Live"]},
            {"styles": ["Live"]},
            {"secondary_types": ["Live"]},
            {"secondary-types": ["Live"]},
            {"title": "Live at Budokan"},
            {"title": "MTV Unplugged in New York"},
            {"title": "The Concert (Live)"},
            {"Title": "Some Album [Live]"},
        ],
    )
    def test_live_signals_detected(self, meta):
        assert _detect_live_performance(meta) is True

    @pytest.mark.parametrize(
        "meta",
        [
            {"genres": ["Rock", "Pop"]},
            {"title": "Studio Album"},
            {"title": "Alive and Well"},  # 'live' substring inside another word must NOT match
            {},
            {"title": ""},
            {"genres": []},
        ],
    )
    def test_studio_signals_do_not_match(self, meta):
        assert _detect_live_performance(meta) is False

    def test_non_dict_input_safe(self):
        assert _detect_live_performance(None) is False
        assert _detect_live_performance("not a dict") is False


# ---------------------------------------------------------------------------
# 2.5 — F16 Container Work aggregation check-constraint behavior
# ---------------------------------------------------------------------------


class TestContainerAggregation:
    def test_add_work_component_succeeds(self, app):
        with app.app_context():
            box = create_work("Catan (Box)")
            rulebook = create_work("Catan — Rulebook")
            agg = add_container_component(
                container_work_id=box.id,
                component_name="Rulebook",
                aggregated_work_id=rulebook.id,
            )
            assert agg.aggregated_type == "work"
            assert agg.aggregated_work_id == rulebook.id
            assert agg.aggregated_item_id is None

    def test_add_item_component_succeeds(self, app):
        with app.app_context():
            from app.db.models import Item, User

            box = create_work("Catan (Box)")
            expr = create_expression(box.id, content_type="board_game")
            manif = create_manifestation(expr.id)

            # Create a physical Item to aggregate
            owner = User(email="owner@example.com", password_hash="x")
            db.session.add(owner)
            db.session.commit()

            board_item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available")
            db.session.add(board_item)
            db.session.commit()

            agg = add_container_component(
                container_work_id=box.id,
                component_name="Main Board",
                aggregated_item_id=board_item.id,
                quantity=1,
            )
            assert agg.aggregated_type == "item"
            assert agg.aggregated_item_id == board_item.id

    def test_add_component_with_both_ids_rejected_by_service(self, app):
        with app.app_context():
            box = create_work("Box")
            rulebook = create_work("Rulebook")
            with pytest.raises(ValueError, match="Exactly one of"):
                add_container_component(
                    container_work_id=box.id,
                    component_name="Bad",
                    aggregated_work_id=rulebook.id,
                    aggregated_item_id=1,  # both set → rejected
                )

    def test_add_component_with_neither_id_rejected_by_service(self, app):
        with app.app_context():
            box = create_work("Box")
            with pytest.raises(ValueError, match="Exactly one of"):
                add_container_component(
                    container_work_id=box.id,
                    component_name="Bad",
                )

    def test_check_constraint_rejects_invalid_row_at_db_layer(self, app):
        """Even bypassing the service helper, the DB CHECK constraint pins the invariant."""
        with app.app_context():
            box = create_work("Box")
            bad = ContainerAggregation(
                container_work_id=box.id,
                aggregated_type="work",
                aggregated_work_id=None,  # violates ck_container_aggregation_type_match
                aggregated_item_id=None,
                component_name="Bad",
                quantity=1,
            )
            db.session.add(bad)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_get_or_create_rulebook_work_idempotent(self, app):
        with app.app_context():
            box = create_work("Catan")
            rb1 = get_or_create_rulebook_work(box)
            rb2 = get_or_create_rulebook_work(box)
            assert rb1.id == rb2.id
            assert rb1.title == "Catan — Rulebook"

            # Container has exactly one Rulebook aggregation
            aggs = ContainerAggregation.query.filter_by(container_work_id=box.id, aggregated_type="work", component_name="Rulebook").all()
            assert len(aggs) == 1
            assert aggs[0].aggregated_work_id == rb1.id

    def test_serialize_container_aggregation(self, app):
        with app.app_context():
            box = create_work("Catan")
            rulebook = get_or_create_rulebook_work(box)

            payload = serialize_container_aggregation(box)
            assert len(payload["works"]) == 1
            assert payload["works"][0]["work_id"] == rulebook.id
            assert payload["works"][0]["component_name"] == "Rulebook"
            assert payload["items"] == []

    def test_serialize_container_aggregation_with_none(self):
        payload = serialize_container_aggregation(None)
        assert payload == {"works": [], "items": []}


# ---------------------------------------------------------------------------
# 2.4 / 2.6b — Payload exposure
# ---------------------------------------------------------------------------


class TestContributionsSerializer:
    def test_serialize_full_frbr_graph(self, app):
        with app.app_context():
            work = create_work("Kind of Blue")
            composer = get_or_create_contributor("Miles Davis")
            add_work_contribution(work.id, composer.id, "composer")

            expr = create_expression(work.id, content_type="music")
            add_expression_contribution(expr.id, composer.id, "performer")

            manif = create_manifestation(expr.id, publisher="Columbia")
            columbia = get_or_create_contributor("Columbia Records", contributor_type="organization")
            add_manifestation_contribution(manif.id, columbia.id, "label")

            payload = serialize_contributions(work=work, expression=expr, manifestation=manif)

            assert [c["name"] for c in payload["creators"]] == ["Miles Davis"]
            assert payload["creators"][0]["role"] == "composer"

            assert [c["name"] for c in payload["performers"]] == ["Miles Davis"]
            assert payload["performers"][0]["role"] == "performer"

            assert [c["name"] for c in payload["publishers"]] == ["Columbia Records"]
            assert payload["publishers"][0]["role"] == "label"

    def test_serialize_handles_missing_entities(self):
        payload = serialize_contributions()
        assert payload == {"creators": [], "performers": [], "publishers": []}

    def test_serialize_handles_partial_graph(self, app):
        with app.app_context():
            work = create_work("Solo Work")
            payload = serialize_contributions(work=work)
            assert payload["creators"] == []
            assert payload["performers"] == []
            assert payload["publishers"] == []


# ---------------------------------------------------------------------------
# Manifestation detail API payload
# ---------------------------------------------------------------------------


class TestManifestationDetailPayload:
    def test_payload_includes_contributions_and_expression_kind(self, app, client):
        with app.app_context():
            work = create_work("Live at the BBC")
            performer = get_or_create_contributor("The Beatles")
            expr = get_or_create_live_performance_expression(
                work_id=work.id,
                content_type="music",
                venue="BBC Maida Vale",
                performers=[("The Beatles", "band")],
            )
            _ = performer  # silence unused warning
            manif = create_manifestation(expr.id, publisher="Apple")

            resp = client.get(f"/api/manifestations/{manif.id}")
            assert resp.status_code == 200
            body = resp.get_json()
            assert body["success"] is True
            data = body["data"]

            assert data["expression_kind"] == "live_performance"
            assert data["is_live_performance"] is True
            assert any(c["name"] == "The Beatles" and c["role"] == "band" for c in data["contributions"]["performers"])
            # Container aggregation present but empty for non-board-game payloads
            assert data["container_aggregation"] == {"works": [], "items": []}

    def test_payload_for_studio_album_marks_not_live(self, app, client):
        with app.app_context():
            work = create_work("Abbey Road")
            expr = create_expression(work.id, content_type="music")
            manif = create_manifestation(expr.id)

            resp = client.get(f"/api/manifestations/{manif.id}")
            assert resp.status_code == 200
            data = resp.get_json()["data"]
            assert data["expression_kind"] is None
            assert data["is_live_performance"] is False

    def test_payload_includes_container_aggregation_for_board_game(self, app, client):
        with app.app_context():
            box = create_work("Catan")
            rulebook = get_or_create_rulebook_work(box)
            expr = create_expression(box.id, content_type="board_game")
            manif = create_manifestation(expr.id)

            resp = client.get(f"/api/manifestations/{manif.id}")
            assert resp.status_code == 200
            data = resp.get_json()["data"]
            works = data["container_aggregation"]["works"]
            assert any(w["work_id"] == rulebook.id and w["component_name"] == "Rulebook" for w in works)


# ---------------------------------------------------------------------------
# Taxonomies facet exposes expression_kinds
# ---------------------------------------------------------------------------


class TestExpressionKindsFacet:
    def test_expression_kinds_in_taxonomies_payload(self, app, client, admin_headers):
        with app.app_context():
            from app.db.models import Item, User

            # Create a live-performance Expression and a studio Expression
            concert_work = create_work("Live Concert")
            live_expr = get_or_create_live_performance_expression(work_id=concert_work.id, content_type="music")
            live_manif = create_manifestation(live_expr.id)

            studio_work = create_work("Studio Album")
            studio_expr = create_expression(studio_work.id, content_type="music")
            studio_manif = create_manifestation(studio_expr.id)

            # Create an Item for each so they appear in the facet scope
            owner = User.query.filter_by(email="admin@iqoqo.cc").first()
            if owner is None:
                owner = User(email="admin@iqoqo.cc", password_hash="x")
                db.session.add(owner)
                db.session.commit()

            for manif in (live_manif, studio_manif):
                item = Item(manifestation_id=manif.id, owner_id=owner.id, status="available")
                db.session.add(item)
            db.session.commit()

            resp = client.get("/api/taxonomies?scope=global", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.get_json()["data"]
            assert "expression_kinds" in data
            assert "live_performance" in data["expression_kinds"]
