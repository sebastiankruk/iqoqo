"""Python-level ontology guards for FRBR/SHACL constraints."""

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

from sqlalchemy import select

from app.db.core import WORK_LINK_TYPE_IS_EXPANSION_OF, WorkExpansionLink
from app.db.games import ContainerAggregation
from app.db.models import db


def validate_work_not_expansion_aggregated(work_id: int) -> None:
    """
    Guard against aggregating an expansion Work into an F16 Container Work.

    An F1_Work that is the target of ``iqoqo:is_expansion_of`` must not be
    aggregated as a Work component into an ``iqoqo:ContainerAggregation``.
    This function mirrors the SHACL ``ExpansionWorkShape`` at runtime.

    Args:
        work_id: The Work ID to validate.

    Raises:
        ValueError: If the Work is an expansion of another Work.
    """
    expansion_link = db.session.execute(
        select(WorkExpansionLink).where(
            WorkExpansionLink.expansion_work_id == work_id,
            WorkExpansionLink.link_type == WORK_LINK_TYPE_IS_EXPANSION_OF,
        )
    ).scalar_one_or_none()
    if expansion_link is not None:
        raise ValueError(
            f"Ontology violation: Work {work_id} is an expansion of "
            f"{expansion_link.base_work_id} and cannot be aggregated into "
            f"an F16 Container Work."
        )


def validate_container_not_linked_as_expansion(container_work_id: int) -> None:
    """
    Guard against declaring an F16 Container Work as an expansion of another Work.

    Args:
        container_work_id: The Work ID being declared as an expansion.

    Raises:
        ValueError: If the Work already aggregates components as an F16
                    Container Work.
    """
    is_container = db.session.execute(
        select(ContainerAggregation).where(
            ContainerAggregation.container_work_id == container_work_id,
        )
    ).scalar_one_or_none()
    if is_container is not None:
        raise ValueError(
            f"Ontology violation: Work {container_work_id} is an F16 Container Work "
            f"and cannot be declared an expansion of another Work."
        )
