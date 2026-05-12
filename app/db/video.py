# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Video/film event-based models (catalog schema).

Implements FRBRoo event-based modeling for video media:
- CreationEvent (WorkContribution) maps to Directors/Writers.
- PerformanceEvent (ExpressionContribution) maps to Cast/Actors.
- PublicationEvent (ManifestationContribution) maps to Studios.
"""

from __future__ import annotations

from app.db.core import _CATALOG, _CATALOG_PFX

from . import db

MANIFESTATION_VIDEO_META_KEYS: tuple[str, ...] = (
    "resolution",
    "aspect_ratio",
    "video_format",
    "audio_formats",
    "region_code",
    "run_time_minutes",
)

WORK_VIDEO_ROLES: tuple[str, ...] = ("director", "writer", "screenwriter", "creator")

EXPRESSION_VIDEO_ROLES: tuple[str, ...] = ("actor", "cast", "voice_actor", "host")

MANIFESTATION_VIDEO_ROLES: tuple[str, ...] = ("studio", "distributor", "producer", "network")


class ManifestationContribution(db.Model):  # type: ignore[name-defined]
    """
    FRBRoo Publication Event.

    Links a Manifestation to a Contributor with a publication role
    (e.g., studio, production company, distributor).
    """

    __tablename__ = "manifestation_contributions"
    __table_args__ = (
        db.Index("ix_manifestation_contributions_manifestation_id", "manifestation_id"),
        db.Index("ix_manifestation_contributions_contributor_id", "contributor_id"),
        *(({"schema": _CATALOG},) if _CATALOG else ()),
    )

    id = db.Column(db.Integer, primary_key=True)
    manifestation_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}manifestations.id", ondelete="CASCADE"), nullable=False)
    contributor_id = db.Column(db.Integer, db.ForeignKey(f"{_CATALOG_PFX}contributors.id", ondelete="CASCADE"), nullable=False)

    #: see MANIFESTATION_VIDEO_ROLES for valid values
    role = db.Column(db.String(100), nullable=False)
    sequence = db.Column(db.Integer, default=0)

    # Note: Contributor relationship can be added here or dynamically accessed via backrefs
    contributor = db.relationship(
        "Contributor", backref=db.backref("manifestation_contributions", lazy="dynamic", cascade="all, delete-orphan")
    )
    manifestation = db.relationship("Manifestation", backref=db.backref("contributions", lazy="dynamic", cascade="all, delete-orphan"))
