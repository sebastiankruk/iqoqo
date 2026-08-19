"""Tests for board game expansion ontology (F1 Work + WorkExpansionLink)."""

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

import pytest

from app.core.frbr_service import add_container_component, create_work, link_expansion_to_base
from app.db.core import WORK_LINK_TYPE_IS_EXPANSION_OF, Work, WorkExpansionLink
from app.db.games import ContainerAggregation
from app.db.models import db


def test_expansion_created_as_f1_work_with_link(app):
    """An expansion is a separate Work linked to the base game, not aggregated."""
    with app.app_context():
        base = create_work(title="Base Game", meta={"type": "board_game"})
        expansion = create_work(title="Base Game: Expansion Pack", meta={"type": "board_game"})

        link = link_expansion_to_base(base.id, expansion.id)

        assert link.base_work_id == base.id
        assert link.expansion_work_id == expansion.id
        assert link.link_type == WORK_LINK_TYPE_IS_EXPANSION_OF

        stored = db.session.get(WorkExpansionLink, link.id)
        assert stored is not None

        # Expansion remains a separate F1_Work
        expansion_work = db.session.get(Work, expansion.id)
        assert expansion_work is not None
        assert expansion_work.title == "Base Game: Expansion Pack"


def test_guard_rejects_aggregating_expansion_into_container(app):
    """Python validator prevents an expansion Work from being aggregated into F16."""
    with app.app_context():
        base = create_work(title="Base Game", meta={"type": "board_game"})
        expansion = create_work(title="Expansion", meta={"type": "board_game"})
        container = create_work(title="Base Game Box", meta={"type": "board_game"})

        link_expansion_to_base(base.id, expansion.id)

        with pytest.raises(ValueError, match="Ontology violation"):
            add_container_component(container.id, "Expansion Rulebook", aggregated_work_id=expansion.id)


def test_guard_rejects_declaring_container_as_expansion(app):
    """Python validator prevents an F16 Container Work from being linked as an expansion."""
    with app.app_context():
        base = create_work(title="Base Game", meta={"type": "board_game"})
        container = create_work(title="Base Game Box", meta={"type": "board_game"})
        rulebook = create_work(title="Rulebook", meta={"type": "board_game"})

        add_container_component(container.id, "Rulebook", aggregated_work_id=rulebook.id)

        with pytest.raises(ValueError, match="Ontology violation"):
            link_expansion_to_base(base.id, container.id)


def test_container_can_still_aggregate_non_expansion_works(app):
    """Non-expansion Works can still be aggregated into F16 Container Works."""
    with app.app_context():
        container = create_work(title="Base Game Box", meta={"type": "board_game"})
        rulebook = create_work(title="Rulebook", meta={"type": "board_game"})

        agg = add_container_component(container.id, "Rulebook", aggregated_work_id=rulebook.id)

        assert agg is not None
        assert agg.aggregated_type == "work"
        assert agg.aggregated_work_id == rulebook.id
        assert db.session.get(ContainerAggregation, agg.id) is not None
