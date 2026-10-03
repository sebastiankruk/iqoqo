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
"""Every column referencing a merged FRBR entity must be in the re-point map.

This is the release gate for the merge-integrity work.  Two shipped data-loss
defects shared a root cause: a table referencing a merged Work was not
re-pointed, and the ``ON DELETE CASCADE`` on that column then destroyed the row.
Neither was visible to code review, and neither was visible to the behavioural
suite, because the aggregate assertions could not tell a deleted reference from a
re-pointed one.

The check is therefore mechanical rather than declarative: it reflects the
SQLAlchemy metadata for every foreign key targeting ``works.id``,
``expressions.id``, and ``manifestations.id`` and asserts each one appears in
the matching tier's map.  Adding a referencing column therefore fails here
rather than silently degrading the next merge.
"""

import pytest

from app.core.frbr_merge import ALLOWED_OMISSIONS, REFPOINTS_BY_TIER
from app.db import contributions, core, games, roadmap, settings, social

#: Modules whose models can declare a foreign key into a merged FRBR tier.
_SOURCED_MODULES = (contributions, core, games, roadmap, settings, social)

#: Tier key -> the table whose primary key that tier's entities use.
TIER_TARGETS = {
    "work": "works",
    "expression": "expressions",
    "manifestation": "manifestations",
}


def _declared_fk_columns() -> dict[str, set[tuple[str, str]]]:
    """Reflect every foreign key that targets an abstract FRBR tier.

    Returns:
        Mapping of tier key to a set of ``(table_name, column_name)`` pairs.
    """
    found: dict[str, set[tuple[str, str]]] = {tier: set() for tier in TIER_TARGETS}
    for module in _SOURCED_MODULES:
        for name in dir(module):
            obj = getattr(module, name)
            table = getattr(obj, "__table__", None)
            if table is None or not hasattr(obj, "__tablename__"):
                continue
            for column in table.columns:
                for fk in column.foreign_keys:
                    # ``target_fullname`` is schema-qualified ("catalog.works.id"),
                    # so keep the last two components: table plus column.
                    parts = fk.target_fullname.split(".")
                    if len(parts) < 2:
                        continue
                    target = ".".join(parts[-2:])
                    for tier, target_table in TIER_TARGETS.items():
                        if target == f"{target_table}.id":
                            found[tier].add((table.name, column.name))
    return found


def _resolve_model(model_name: str):
    """Return the model class named in an ``ALLOWED_OMISSIONS`` entry.

    Args:
        model_name: Class name as written in the allowlist.

    Returns:
        The model class, or ``None`` when no sourced module declares it.
    """
    for module in _SOURCED_MODULES:
        candidate = getattr(module, model_name, None)
        if candidate is not None and hasattr(candidate, "__tablename__"):
            return candidate
    return None


def _mapped_columns(tier: str) -> set[tuple[str, str]]:
    """Return the ``(table, column)`` pairs a tier's map re-points.

    Args:
        tier: FRBR level key.

    Returns:
        The mapped pairs.  Polymorphic SemanticLink is excluded because it
        declares no foreign key, so reflection never reports it.
    """
    return {(refpoint.model.__tablename__, refpoint.fk_attribute) for refpoint in REFPOINTS_BY_TIER[tier] if not refpoint.polymorphic}


def test_every_tier_is_present_in_the_map():
    """Each abstract FRBR level must have a re-point map."""
    assert set(REFPOINTS_BY_TIER) == set(TIER_TARGETS)


@pytest.mark.parametrize("tier", sorted(TIER_TARGETS))
def test_every_referencing_column_is_repointed(tier):
    """No column may reference a merged tier without being re-pointed.

    This is the gate that would have caught both shipped data-loss defects.
    """
    allowed = set()
    for model_name, column in ALLOWED_OMISSIONS[tier]:
        model = _resolve_model(model_name)
        assert model is not None, f"{tier}: ALLOWED_OMISSIONS names unknown model {model_name!r}"
        allowed.add((model.__tablename__, column))

    declared = _declared_fk_columns()[tier]
    uncovered = declared - _mapped_columns(tier) - allowed
    assert not uncovered, (
        f"{len(uncovered)} column(s) reference the {tier} tier but are absent from "
        f"frbr_merge.REFPOINTS_BY_TIER[{tier!r}]. A merge would leave these rows pointing at a "
        f"deleted row (destroyed, if ON DELETE CASCADE) or orphaned (if SET NULL). Add them to the "
        f"tier's map, or record an explicit justification in ALLOWED_OMISSIONS: {sorted(uncovered)}"
    )


def test_allowed_omissions_are_actually_omissions():
    """Each allowlist entry must name a real column that really is unmapped.

    A stale allowlist entry would silently excuse a genuine data-loss path.
    """
    for tier, entries in ALLOWED_OMISSIONS.items():
        declared = _declared_fk_columns()[tier]
        mapped = _mapped_columns(tier)
        for model_name, column in sorted(entries):
            model = _resolve_model(model_name)
            assert model is not None, f"{tier}: allowlist names unknown model {model_name!r}"
            pair = (model.__tablename__, column)
            assert pair in declared, f"{tier}: {pair} is in ALLOWED_OMISSIONS but declares no such foreign key"
            assert pair not in mapped, f"{tier}: {pair} is in ALLOWED_OMISSIONS but is already re-pointed"


def test_map_counts_match_the_documented_totals():
    """Keep the module docstring's counts honest.

    The docstring in ``app/core/frbr_merge.py`` states 13/7/9 real foreign keys
    per tier, each plus one polymorphic ``SemanticLink`` entry; this fails if a
    column is added without the documentation being updated.
    """
    documented = {"work": 13, "expression": 7, "manifestation": 9}
    actual = {tier: len([r for r in refpoints if not r.polymorphic]) for tier, refpoints in REFPOINTS_BY_TIER.items()}
    assert actual == documented, f"frbr_merge module docstring counts are stale: {actual} != {documented}"


def test_semantic_link_is_repointed_once_per_tier():
    """SemanticLink is polymorphic, so each tier maps it explicitly."""
    for tier in TIER_TARGETS:
        polymorphic = [r for r in REFPOINTS_BY_TIER[tier] if r.polymorphic]
        assert len(polymorphic) == 1, f"{tier}: expected exactly one polymorphic SemanticLink refpoint"
        assert polymorphic[0].model is core.SemanticLink
