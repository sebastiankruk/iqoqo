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
"""Tests for Python-level ontology runtime validation guards."""

import pytest

from app.core.ontology_validation import (
    validate_container_not_linked_as_expansion,
    validate_work_not_expansion_aggregated,
)
from app.db.core import WORK_LINK_TYPE_IS_EXPANSION_OF, Work, WorkExpansionLink
from app.db.games import ContainerAggregation
from app.db.models import db


def test_validate_work_not_expansion_aggregated_passes_when_independent(app):
    """An independent Work with no expansion link passes validation."""
    with app.app_context():
        work = Work(title="Base Work Standalone")
        db.session.add(work)
        db.session.commit()

        # Should not raise
        validate_work_not_expansion_aggregated(work.id)


def test_validate_work_not_expansion_aggregated_raises_when_expansion(app):
    """A Work linked as an expansion of another Work raises ValueError on aggregation."""
    with app.app_context():
        base = Work(title="Catan Base Game")
        expansion = Work(title="Catan 5-6 Player Extension")
        db.session.add_all([base, expansion])
        db.session.commit()

        link = WorkExpansionLink(
            base_work_id=base.id,
            expansion_work_id=expansion.id,
            link_type=WORK_LINK_TYPE_IS_EXPANSION_OF,
        )
        db.session.add(link)
        db.session.commit()

        with pytest.raises(ValueError, match="is an expansion of .* and cannot be aggregated"):
            validate_work_not_expansion_aggregated(expansion.id)


def test_validate_container_not_linked_as_expansion_passes_when_not_container(app):
    """A standard non-container Work passes validation."""
    with app.app_context():
        work = Work(title="Regular Book Work")
        db.session.add(work)
        db.session.commit()

        # Should not raise
        validate_container_not_linked_as_expansion(work.id)


def test_validate_container_not_linked_as_expansion_raises_when_aggregating(app):
    """An F16 Container Work that aggregates components raises ValueError if declared as expansion."""
    with app.app_context():
        container = Work(title="Big Box Board Game")
        component = Work(title="Rulebook Work")
        db.session.add_all([container, component])
        db.session.commit()

        agg = ContainerAggregation(
            container_work_id=container.id,
            aggregated_type="work",
            aggregated_work_id=component.id,
            component_name="Rulebook",
            quantity=1,
        )
        db.session.add(agg)
        db.session.commit()

        with pytest.raises(ValueError, match="is an F16 Container Work and cannot be declared an expansion"):
            validate_container_not_linked_as_expansion(container.id)
