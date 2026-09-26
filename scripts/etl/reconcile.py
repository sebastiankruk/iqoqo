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
"""FRBR entity relationship inventory and reconciliation policies.

Defines ReparentPolicy, RelationshipInventory, and inventory builders for
Work and Manifestation entities, along with ISBN normalization utilities.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

ISBN_CLEAN_PATTERN = re.compile(r"[^0-9X]")


class ReparentPolicy(Enum):
    """Policy for handling dependent records during merge."""

    REPARENT = "reparent"  # Move to canonical entity
    DELETE = "delete"  # Delete if duplicate would conflict
    ABORT = "abort"  # Abort merge if conflict detected
    MERGE_METADATA = "merge_metadata"  # Merge JSON metadata fields


@dataclass
class RelationshipInventory:
    """Complete inventory of relationships for an entity type."""

    entity_type: str  # "Work" or "Manifestation"
    relationships: list[dict[str, Any]] = field(default_factory=list)

    def add_relationship(
        self,
        model_class: str,
        fk_column: str,
        policy: ReparentPolicy,
        unique_constraint: str | None = None,
        notes: str = "",
    ) -> None:
        """Add a relationship to the inventory."""
        self.relationships.append(
            {
                "model": model_class,
                "fk_column": fk_column,
                "policy": policy.value,
                "unique_constraint": unique_constraint,
                "notes": notes,
            }
        )


def build_work_relationship_inventory() -> RelationshipInventory:
    """Build complete relationship inventory for Work entity."""
    inventory = RelationshipInventory(entity_type="Work")

    # Core FRBR relationships
    inventory.add_relationship(
        model_class="Expression",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Expressions are reparented to canonical Work",
    )

    # Contribution relationships
    inventory.add_relationship(
        model_class="WorkContribution",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Contributions are reparented to canonical Work",
    )

    # Work part relationships (container)
    inventory.add_relationship(
        model_class="WorkPart",
        fk_column="container_work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Work parts where this Work is container are reparented",
    )

    # Work part relationships (member)
    inventory.add_relationship(
        model_class="WorkPart",
        fk_column="part_work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Work parts where this Work is member are reparented",
    )

    # Expansion relationships
    inventory.add_relationship(
        model_class="WorkExpansionLink",
        fk_column="base_work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Expansion links where this Work is base are reparented",
    )

    inventory.add_relationship(
        model_class="WorkExpansionLink",
        fk_column="expansion_work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Expansion links where this Work is expansion are reparented",
    )

    # User intent relationships
    inventory.add_relationship(
        model_class="UserWorkIntent",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        unique_constraint="uq_user_work_intent",
        notes="User intents are reparented; conflicts abort merge",
    )

    # Social feedback relationships
    inventory.add_relationship(
        model_class="SocialFeedback",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        unique_constraint="uq_user_work_feedback",
        notes="Feedback is reparented; conflicts abort merge",
    )

    # Social note relationships
    inventory.add_relationship(
        model_class="SocialNote",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Notes are reparented to canonical Work",
    )

    # Escalation request relationships
    inventory.add_relationship(
        model_class="EscalationRequest",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Escalation requests are reparented",
    )

    # Audit log relationships
    inventory.add_relationship(
        model_class="EntityAuditLog",
        fk_column="work_id",
        policy=ReparentPolicy.REPARENT,
        notes="Audit logs are reparented",
    )

    return inventory


def build_manifestation_relationship_inventory() -> RelationshipInventory:
    """Build complete relationship inventory for Manifestation entity."""
    inventory = RelationshipInventory(entity_type="Manifestation")

    # Core FRBR relationships
    inventory.add_relationship(
        model_class="Item",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Items are reparented to canonical Manifestation",
    )

    # Image scan relationships
    inventory.add_relationship(
        model_class="ImageScan",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Image scans are reparented to canonical Manifestation",
    )

    # Contribution relationships
    inventory.add_relationship(
        model_class="ManifestationContribution",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Contributions are reparented to canonical Manifestation",
    )

    # Item status log relationships
    inventory.add_relationship(
        model_class="ItemStatusLog",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Status logs are reparented",
    )

    # Item tag relationships (via Item)
    inventory.add_relationship(
        model_class="ItemTag",
        fk_column="item_id",
        policy=ReparentPolicy.REPARENT,
        notes="Item tags follow Item reparenting",
    )

    # Social feedback relationships
    inventory.add_relationship(
        model_class="SocialFeedback",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        unique_constraint="uq_user_manifestation_feedback",
        notes="Feedback is reparented; conflicts abort merge",
    )

    # Social note relationships
    inventory.add_relationship(
        model_class="SocialNote",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Notes are reparented to canonical Manifestation",
    )

    # Escalation request relationships
    inventory.add_relationship(
        model_class="EscalationRequest",
        fk_column="manifestation_id",
        policy=ReparentPolicy.REPARENT,
        notes="Escalation requests are reparented",
    )

    # Metadata reparenting
    inventory.add_relationship(
        model_class="Manifestation",
        fk_column="meta",
        policy=ReparentPolicy.MERGE_METADATA,
        notes="JSON metadata is merged from duplicate to canonical",
    )

    return inventory


def isbn10_to_isbn13(isbn10: str) -> str | None:
    """Convert a valid 10-digit ISBN into a standard 13-digit EAN-13 ISBN.

    :param isbn10: Raw or formatted 10-digit ISBN string
    :return: Normalized 13-digit ISBN string or None if invalid
    """
    cleaned = ISBN_CLEAN_PATTERN.sub("", isbn10.upper())
    if len(cleaned) != 10:
        return None

    # Validate 10-digit checksum
    if not (cleaned[:9].isdigit() and (cleaned[9].isdigit() or cleaned[9] == "X")):
        return None
    total10 = sum((10 - idx) * (10 if char == "X" else int(char)) for idx, char in enumerate(cleaned))
    if total10 % 11 != 0:
        return None

    # Construct 13-digit prefix (978 + first 9 digits)
    core = f"978{cleaned[:9]}"
    total13 = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(core))
    check13 = (10 - (total13 % 10)) % 10
    return f"{core}{check13}"


def normalize_to_isbn13(raw_isbn: str) -> str | None:
    """Normalize any ISBN (10-digit or 13-digit) to a canonical 13-digit string.

    :param raw_isbn: Raw ISBN string containing possible hyphens or spaces
    :return: Normalized 13-digit ISBN or None if invalid
    """
    cleaned = ISBN_CLEAN_PATTERN.sub("", raw_isbn.upper())
    if len(cleaned) == 10:
        return isbn10_to_isbn13(cleaned)
    if len(cleaned) == 13 and cleaned.isdigit():
        total = sum(int(digit) * (1 if idx % 2 == 0 else 3) for idx, digit in enumerate(cleaned[:12]))
        expected_check = (10 - (total % 10)) % 10
        if int(cleaned[12]) == expected_check:
            return cleaned
    return None


# Alias for cleaner API
normalize_isbn = normalize_to_isbn13
