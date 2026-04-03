# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Board Game container models (catalog schema).

Implements FRBRoo F16 Container Work modeling for board games.
The board game box acts as an F16 Container aggregating:
- F1 Works (e.g., Rulebooks, Scenarios)
- F5 Items (e.g., Game Board, Meeples, Dice, Cards)
"""

from __future__ import annotations

from app.db.core import _CATALOG, _CATALOG_PFX, _INVENTORY_PFX

from . import db

MANIFESTATION_GAME_META_KEYS: tuple[str, ...] = ("min_players", "max_players", "playtime_minutes", "min_age", "game_mechanics", "designer")


class ContainerAggregation(db.Model):  # type: ignore[name-defined]
    """
    FRBRoo F16 Container Work Aggregation.

    Polymorphic link representing contents within a board game box.
    Links the parent container Work to either abstract Works (rulebooks)
    or physical Items (boards, pieces).
    """

    __tablename__ = "container_aggregations"
    __table_args__ = (
        db.Index("ix_container_aggregations_container_work_id", "container_work_id"),
        *(({"schema": _CATALOG},) if _CATALOG else ()),
    )

    id = db.Column(db.Integer, primary_key=True)
    container_work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), nullable=False)

    #: Type of aggregated component: 'work' or 'item'
    aggregated_type = db.Column(db.String(50), nullable=False)

    #: Populated if aggregated_type == 'work' (e.g., Rulebook)
    aggregated_work_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}works.id", ondelete="CASCADE"), nullable=True)

    #: Populated if aggregated_type == 'item' (e.g., Game Board, Pieces)
    aggregated_item_id = db.Column(db.Integer, db.ForeignKey(f"{_INVENTORY_PFX}items.id", ondelete="CASCADE"), nullable=True)

    #: Human-readable name of the component (e.g., "Main Board", "Red Meeples")
    component_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    # Relationships
    container_work = db.relationship("Work", foreign_keys=[container_work_id], backref=db.backref("aggregates", lazy="dynamic"))
    aggregated_work = db.relationship("Work", foreign_keys=[aggregated_work_id])
    aggregated_item = db.relationship("Item", foreign_keys=[aggregated_item_id])
