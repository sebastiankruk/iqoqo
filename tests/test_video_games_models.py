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

"""Integration tests for Video and Board Game FRBRoo ontology expansions."""

import pytest

from app.db import db
from app.db.audio import Contributor
from app.db.core import Expression, Manifestation, Work
from app.db.games import ContainerAggregation
from app.db.video import ManifestationContribution


def test_video_manifestation_contribution(app):
    """Test linking a studio/distributor to a video manifestation (Publication Event)."""
    with app.app_context():
        # 1. Setup Base FRBR Entities
        work = Work(title="Dune: Part Two")
        db.session.add(work)
        db.session.flush()

        expression = Expression(work_id=work.id, content_type="video", language="en")
        db.session.add(expression)
        db.session.flush()

        manifestation = Manifestation(
            expression_id=expression.id,
            isbn13="88392982121",  # Example UPC/EAN acting as ID
            meta={"resolution": "4K", "run_time_minutes": 166},
        )
        db.session.add(manifestation)
        db.session.flush()

        # 2. Setup Contributor
        studio = Contributor(name="Legendary Pictures", type="organization")
        db.session.add(studio)
        db.session.flush()

        # 3. Add Manifestation Contribution
        contrib = ManifestationContribution(manifestation_id=manifestation.id, contributor_id=studio.id, role="studio")
        db.session.add(contrib)
        db.session.commit()

        # Verify
        assert contrib.id is not None
        assert contrib.contributor.name == "Legendary Pictures"
        # Accessing manifestation via backref
        assert manifestation.contributions.first().role == "studio"
        assert manifestation.meta["run_time_minutes"] == 166
        assert contrib.role == "studio"


def test_board_game_container_aggregation(app):
    """Test F16 Container Work aggregation for board games."""
    with app.app_context():
        # 1. Setup FRBR for the Container (The Box)
        box_work = Work(title="Twilight Imperium (Fourth Edition)")
        db.session.add(box_work)
        db.session.flush()

        # 2. Setup component (Work -> Rulebook)
        rulebook = Work(title="Learn to Play Guide")
        db.session.add(rulebook)
        db.session.flush()

        # 3. Add Aggregation Link
        agg = ContainerAggregation(
            container_work_id=box_work.id, aggregated_type="work", aggregated_work_id=rulebook.id, component_name="Rulebook", quantity=1
        )
        db.session.add(agg)
        db.session.commit()

        # Verify
        assert agg.id is not None
        assert agg.container_work.title == "Twilight Imperium (Fourth Edition)"
        assert agg.aggregated_work.title == "Learn to Play Guide"
        assert agg.component_name == "Rulebook"
        assert agg.aggregated_type == "work"


def test_board_game_invalid_aggregation(app):
    """Test that invalid ContainerAggregation states are rejected by DB constraint."""
    from sqlalchemy.exc import IntegrityError

    with app.app_context():
        # 1. Setup Container
        box_work = Work(title="Catan")
        db.session.add(box_work)
        db.session.flush()

        # 2. Try to add invalid (both NULL)
        invalid_null = ContainerAggregation(container_work_id=box_work.id, aggregated_type="work", component_name="Invalid")
        db.session.add(invalid_null)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # 3. Setup Work and Item for "both NOT NULL" test
        rulebook = Work(title="Catan Rules")
        db.session.add(rulebook)
        db.session.flush()

        # 4. Try to add invalid (both NOT NULL)
        invalid_both = ContainerAggregation(
            container_work_id=box_work.id,
            aggregated_type="work",
            aggregated_work_id=rulebook.id,
            aggregated_item_id=1,  # Should be NULL for type 'work'
            component_name="Invalid Both",
        )
        db.session.add(invalid_both)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
