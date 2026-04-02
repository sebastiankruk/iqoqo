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
"""Tests for audio / event-based data models (0.1.3 additions).

Covers:
- Contributor CRUD and deduplication
- WorkContribution (FRBRoo Composition Event) creation and relationship traversal
- ExpressionContribution (FRBRoo Performance Event) creation and relationship traversal
- WorkPart (FRBRoo F15 Complex Work) containment
- Cascade deletes — removing a Work cleans up contributions and work-parts
- MANIFESTATION_AUDIO_META_KEYS and role constants are non-empty tuples of strings
- frbr_service helpers for the new models
"""

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names intentionally

import io

import pytest

from app.db.audio import (
    EXPRESSION_CONTRIBUTION_ROLES,
    MANIFESTATION_AUDIO_META_KEYS,
    WORK_CONTRIBUTION_ROLES,
    Contributor,
    ExpressionContribution,
    WorkContribution,
    WorkPart,
)
from app.db.core import Expression, Item, Manifestation, Work
from app.db.models import db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def work(app):
    """Persist a minimal Work and return it."""
    with app.app_context():
        w = Work(title="Kind of Blue", meta={"original_language": "en"})
        db.session.add(w)
        db.session.commit()
        yield w


@pytest.fixture
def expression(app, work):
    """Persist a sound Expression for the work fixture."""
    with app.app_context():
        expr = Expression(work_id=work.id, content_type="sound", language="en")
        db.session.add(expr)
        db.session.commit()
        yield expr


@pytest.fixture
def contributor_person(app):
    """Persist a person Contributor."""
    with app.app_context():
        c = Contributor(name="Miles Davis", type="person")
        db.session.add(c)
        db.session.commit()
        yield c


@pytest.fixture
def contributor_band(app):
    """Persist an organization Contributor."""
    with app.app_context():
        c = Contributor(name="Miles Davis Sextet", type="organization")
        db.session.add(c)
        db.session.commit()
        yield c


# ---------------------------------------------------------------------------
# Contributor
# ---------------------------------------------------------------------------


class TestContributor:
    def test_create_person(self, app, contributor_person):
        """A person Contributor persists with correct fields."""
        with app.app_context():
            c = db.session.get(Contributor, contributor_person.id)
            assert c is not None
            assert c.name == "Miles Davis"
            assert c.type == "person"

    def test_create_organization(self, app, contributor_band):
        """An organization Contributor persists with correct fields."""
        with app.app_context():
            c = db.session.get(Contributor, contributor_band.id)
            assert c is not None
            assert c.type == "organization"

    def test_default_type_is_person(self, app):
        """The default contributor type is 'person'."""
        with app.app_context():
            c = Contributor(name="Thelonious Monk")
            db.session.add(c)
            db.session.commit()
            assert c.type == "person"

    def test_meta_defaults_to_dict(self, app):
        """meta column defaults to an empty dict (not None)."""
        with app.app_context():
            c = Contributor(name="John Coltrane", type="person")
            db.session.add(c)
            db.session.commit()
            assert c.meta is not None


# ---------------------------------------------------------------------------
# WorkContribution  (Composition Event)
# ---------------------------------------------------------------------------


class TestWorkContribution:
    def test_create(self, app, work, contributor_person):
        """WorkContribution links a contributor to a work with a role."""
        with app.app_context():
            wc = WorkContribution(
                work_id=work.id,
                contributor_id=contributor_person.id,
                role="composer",
                sequence=0,
            )
            db.session.add(wc)
            db.session.commit()

            saved = db.session.get(WorkContribution, wc.id)
            assert saved is not None
            assert saved.work_id == work.id
            assert saved.contributor_id == contributor_person.id
            assert saved.role == "composer"

    def test_relationship_via_work(self, app, work, contributor_person):
        """Work.contributions relationship returns the linked WorkContribution."""
        with app.app_context():
            wc = WorkContribution(work_id=work.id, contributor_id=contributor_person.id, role="composer")
            db.session.add(wc)
            db.session.commit()

            refreshed_work = db.session.get(Work, work.id)
            assert any(c.contributor_id == contributor_person.id for c in refreshed_work.contributions)

    def test_sequence_ordering(self, app, work, contributor_person, contributor_band):
        """Multiple contributions on the same work are stored with distinct sequences."""
        with app.app_context():
            first = WorkContribution(work_id=work.id, contributor_id=contributor_person.id, role="composer", sequence=0)
            second = WorkContribution(work_id=work.id, contributor_id=contributor_band.id, role="lyricist", sequence=1)
            db.session.add_all([first, second])
            db.session.commit()

            sequences = [c.sequence for c in WorkContribution.query.filter_by(work_id=work.id).all()]
            assert sorted(sequences) == [0, 1]

    def test_cascade_delete_with_work(self, app, work, contributor_person):
        """Deleting a Work cascades and removes its WorkContributions."""
        with app.app_context():
            wc = WorkContribution(work_id=work.id, contributor_id=contributor_person.id, role="composer")
            db.session.add(wc)
            db.session.commit()
            wc_id = wc.id

            db.session.delete(db.session.get(Work, work.id))
            db.session.commit()

            assert db.session.get(WorkContribution, wc_id) is None


# ---------------------------------------------------------------------------
# ExpressionContribution  (Performance Event)
# ---------------------------------------------------------------------------


class TestExpressionContribution:
    def test_create(self, app, expression, contributor_person):
        """ExpressionContribution links a contributor to an expression."""
        with app.app_context():
            ec = ExpressionContribution(
                expression_id=expression.id,
                contributor_id=contributor_person.id,
                role="performer",
                sequence=0,
            )
            db.session.add(ec)
            db.session.commit()

            saved = db.session.get(ExpressionContribution, ec.id)
            assert saved is not None
            assert saved.expression_id == expression.id
            assert saved.role == "performer"

    def test_relationship_via_expression(self, app, expression, contributor_person):
        """Expression.contributions relationship returns the linked ExpressionContribution."""
        with app.app_context():
            ec = ExpressionContribution(expression_id=expression.id, contributor_id=contributor_person.id, role="conductor")
            db.session.add(ec)
            db.session.commit()

            refreshed_expr = db.session.get(Expression, expression.id)
            assert any(c.contributor_id == contributor_person.id for c in refreshed_expr.contributions)

    def test_cascade_delete_with_expression(self, app, expression, contributor_person):
        """Deleting an Expression cascades and removes its ExpressionContributions."""
        with app.app_context():
            ec = ExpressionContribution(expression_id=expression.id, contributor_id=contributor_person.id, role="performer")
            db.session.add(ec)
            db.session.commit()
            ec_id = ec.id

            # Delete expression (work is still present)
            db.session.delete(db.session.get(Expression, expression.id))
            db.session.commit()

            assert db.session.get(ExpressionContribution, ec_id) is None


# ---------------------------------------------------------------------------
# WorkPart  (F15 Complex Work — box-set containment)
# ---------------------------------------------------------------------------


class TestWorkPart:
    def test_create_containment(self, app):
        """A container Work can have a part Work added via WorkPart."""
        with app.app_context():
            container = Work(title="Miles Davis Complete Columbia Box Set")
            part = Work(title="Kind of Blue")
            db.session.add_all([container, part])
            db.session.flush()

            wp = WorkPart(container_work_id=container.id, part_work_id=part.id, sequence=1)
            db.session.add(wp)
            db.session.commit()

            saved = db.session.get(WorkPart, (container.id, part.id))
            assert saved is not None
            assert saved.sequence == 1

    def test_parts_relationship_on_work(self, app):
        """Work.parts relationship lists all WorkPart rows for a container."""
        with app.app_context():
            container = Work(title="Box Set")
            part1 = Work(title="Album 1")
            part2 = Work(title="Album 2")
            db.session.add_all([container, part1, part2])
            db.session.flush()

            db.session.add(WorkPart(container_work_id=container.id, part_work_id=part1.id, sequence=0))
            db.session.add(WorkPart(container_work_id=container.id, part_work_id=part2.id, sequence=1))
            db.session.commit()

            refreshed = db.session.get(Work, container.id)
            assert len(refreshed.parts) == 2
            assert {wp.part_work_id for wp in refreshed.parts} == {part1.id, part2.id}

    def test_member_of_relationship_on_work(self, app):
        """Work.member_of relationship shows which containers a Work belongs to."""
        with app.app_context():
            container = Work(title="Box Set")
            member = Work(title="Album 1")
            db.session.add_all([container, member])
            db.session.flush()

            db.session.add(WorkPart(container_work_id=container.id, part_work_id=member.id))
            db.session.commit()

            refreshed_member = db.session.get(Work, member.id)
            assert any(wp.container_work_id == container.id for wp in refreshed_member.member_of)

    def test_cascade_delete_container(self, app):
        """Deleting the container Work cascades and removes WorkPart rows."""
        with app.app_context():
            container = Work(title="Box Set")
            part = Work(title="Album")
            db.session.add_all([container, part])
            db.session.flush()

            wp = WorkPart(container_work_id=container.id, part_work_id=part.id)
            db.session.add(wp)
            db.session.commit()

            db.session.delete(db.session.get(Work, container.id))
            db.session.commit()

            assert db.session.get(WorkPart, (container.id, part.id)) is None
            # The part Work itself must survive
            assert db.session.get(Work, part.id) is not None


# ---------------------------------------------------------------------------
# frbr_service helpers
# ---------------------------------------------------------------------------


class TestFrbrServiceAudioHelpers:
    def test_get_or_create_contributor_creates(self, app):
        """get_or_create_contributor creates a new contributor when none exists."""
        from app.core.frbr_service import get_or_create_contributor

        with app.app_context():
            c = get_or_create_contributor("Wayne Shorter", "person")
            assert c.id is not None
            assert c.name == "Wayne Shorter"

    def test_get_or_create_contributor_deduplicates(self, app):
        """Calling get_or_create_contributor twice with the same name returns the same row."""
        from app.core.frbr_service import get_or_create_contributor

        with app.app_context():
            c1 = get_or_create_contributor("Bill Evans", "person")
            c2 = get_or_create_contributor("Bill Evans", "person")
            assert c1.id == c2.id

    def test_add_work_contribution(self, app, work, contributor_person):
        """add_work_contribution persists a WorkContribution row."""
        from app.core.frbr_service import add_work_contribution

        with app.app_context():
            wc = add_work_contribution(work.id, contributor_person.id, "composer")
            assert wc.id is not None
            assert wc.role == "composer"

    def test_add_expression_contribution(self, app, expression, contributor_person):
        """add_expression_contribution persists an ExpressionContribution row."""
        from app.core.frbr_service import add_expression_contribution

        with app.app_context():
            ec = add_expression_contribution(expression.id, contributor_person.id, "performer")
            assert ec.id is not None
            assert ec.role == "performer"

    def test_create_work_part(self, app):
        """create_work_part persists a WorkPart relationship."""
        from app.core.frbr_service import create_work_part

        with app.app_context():
            container = Work(title="Complete Works Box")
            part = Work(title="First Album")
            db.session.add_all([container, part])
            db.session.flush()

            wp = create_work_part(container.id, part.id, sequence=1)
            assert wp.container_work_id == container.id
            assert wp.part_work_id == part.id
            assert wp.sequence == 1


# ---------------------------------------------------------------------------
# Constant integrity checks
# ---------------------------------------------------------------------------


class TestConstants:
    def test_manifestation_audio_meta_keys_non_empty(self):
        """MANIFESTATION_AUDIO_META_KEYS is a non-empty tuple of strings."""
        assert len(MANIFESTATION_AUDIO_META_KEYS) > 0
        assert all(isinstance(k, str) and k.strip() for k in MANIFESTATION_AUDIO_META_KEYS)

    def test_work_contribution_roles_non_empty(self):
        """WORK_CONTRIBUTION_ROLES is a non-empty tuple of strings."""
        assert len(WORK_CONTRIBUTION_ROLES) > 0
        assert all(isinstance(r, str) and r.strip() for r in WORK_CONTRIBUTION_ROLES)

    def test_expression_contribution_roles_non_empty(self):
        """EXPRESSION_CONTRIBUTION_ROLES is a non-empty tuple of strings."""
        assert len(EXPRESSION_CONTRIBUTION_ROLES) > 0
        assert all(isinstance(r, str) and r.strip() for r in EXPRESSION_CONTRIBUTION_ROLES)

    @pytest.mark.parametrize("key", MANIFESTATION_AUDIO_META_KEYS)
    def test_audio_meta_key_is_snake_case(self, key):
        """Each audio meta key uses snake_case (no spaces, no hyphens)."""
        assert " " not in key and "-" not in key, f"Key {key!r} should be snake_case"


class TestManifestationImages:
    """Tests for secondary image uploads and persistence."""

    def test_upload_additional_image(self, app, client, admin_headers):
        """Manifestation.meta['additional_images'] stores labels and URLs correctly."""

        with app.app_context():
            # 1. Create a test manifestation
            w = Work(title="Images Test")
            db.session.add(w)
            db.session.flush()
            e = Expression(work_id=w.id, content_type="sound", language="en")
            db.session.add(e)
            db.session.flush()
            m = Manifestation(expression_id=e.id, isbn13="9780000000000")
            db.session.add(m)
            db.session.commit()
            m_id = m.id

        # 2. Upload an image via API
        # 1x1 valid PNG
        img_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        data = {"image": (io.BytesIO(img_content), "disc.jpg"), "label": "disc"}

        res = client.post(f"/api/manifestations/{m_id}/images", data=data, content_type="multipart/form-data", headers=admin_headers)

        assert res.status_code == 201
        assert res.json["success"] is True
        images = res.json["data"]
        assert len(images) == 1
        assert images[0]["label"] == "disc"
        assert "disc.jpg" in images[0]["url"]

        # 3. Verify in DB
        with app.app_context():
            manif = db.session.get(Manifestation, m_id)
            assert "additional_images" in manif.meta
            assert manif.meta["additional_images"][0]["label"] == "disc"
