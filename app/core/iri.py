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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Canonical Linked Data IRI helpers shared by FRBR models and serializers."""

from __future__ import annotations

import os
from urllib.parse import quote

DEFAULT_LOD_BASE_URL = "https://iqoqo.cc"

FRBR_IRI_SEGMENTS: dict[str, str] = {
    "work": "works",
    "expression": "expressions",
    "manifestation": "manifestations",
    "item": "items",
}


def get_lod_base_url() -> str:
    """Return the configured canonical base URL for Linked Data identifiers."""
    base_url = os.environ.get("BASE_URL") or os.environ.get("NEXT_PUBLIC_FRONTEND_URL") or DEFAULT_LOD_BASE_URL
    return base_url.rstrip("/")


def canonical_frbr_iri(entity_type: str, entity_id: object, base_url: str | None = None) -> str:
    """Build the canonical IRI for one persisted FRBR entity.

    API endpoints are dereferencing routes only. They must not be minted as RDF
    identities; the canonical policy is ``{BASE_URL}/{plural-kind}/{id}``.
    """
    try:
        segment = FRBR_IRI_SEGMENTS[entity_type.lower()]
    except (AttributeError, KeyError) as exc:
        raise ValueError(f"Unsupported FRBR entity type: {entity_type!r}") from exc
    if entity_id is None or str(entity_id) == "":
        raise ValueError("A FRBR entity IRI requires a non-empty identifier")
    base = (base_url or get_lod_base_url()).rstrip("/")
    return f"{base}/{segment}/{quote(str(entity_id), safe='-._~')}"


def canonical_related_iri(entity_type: str, entity_id: object, base_url: str) -> str:
    """Build canonical non-FRBR related-resource IRIs used by RDF enrichment."""
    if entity_type not in {"contributors", "collections"}:
        raise ValueError(f"Unsupported related entity type: {entity_type!r}")
    if entity_id is None or str(entity_id) == "":
        raise ValueError("A related entity IRI requires a non-empty identifier")
    return f"{base_url.rstrip('/')}/{entity_type}/{quote(str(entity_id), safe='-._~')}"
