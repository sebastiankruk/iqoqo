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
"""Public API re-export shim for iqoqo v0.7.0.

Backward-compatibility shim preserving all imports and monkeypatches from app.api.public.
The implementation has been decomposed into:
- app.api.public_rdf: Linked Open Data, canonical IRIs, and RDF endpoints.
- app.api.public_profile: Public user profiles and inventory check.
- app.api.public_items: Item grids, collection feeds, shared tokens, and sitemaps.
"""

import sys
from typing import Any

from app.api import public_items, public_profile, public_rdf
from app.api.public_items import (
    fetch_global_fresh_arrivals,
    fetch_shared_collection_by_token,
    fetch_user_public_collection,
    generate_rss_xml,
    generate_sitemap_xml,
    get_public_items,
    get_shared_collection,
    global_fresh_feed,
    shared_collection_feed,
    sitemap,
    user_collection_feed,
)
from app.api.public_profile import (
    check_inventory,
    get_public_profile,
)
from app.api.public_rdf import (
    DEFAULT_PUBLIC_RDF_LIMIT,
    MAX_PUBLIC_RDF_LIMIT,
    MIN_PUBLIC_RDF_LIMIT,
    _negotiate_rdf_format,
    _parse_safe_rdf_limit,
    _prefers_html,
    add_cors_headers,
    canonical_expression_iri,
    canonical_item_iri,
    canonical_manifestation_iri,
    canonical_work_iri,
    get_public_expression,
    get_public_item,
    get_public_manifestation,
    get_public_work,
    lod_bp,
    public_bp,
)

__all__ = [
    "DEFAULT_PUBLIC_RDF_LIMIT",
    "MAX_PUBLIC_RDF_LIMIT",
    "MIN_PUBLIC_RDF_LIMIT",
    "_negotiate_rdf_format",
    "_parse_safe_rdf_limit",
    "_prefers_html",
    "add_cors_headers",
    "canonical_expression_iri",
    "canonical_item_iri",
    "canonical_manifestation_iri",
    "canonical_work_iri",
    "check_inventory",
    "fetch_global_fresh_arrivals",
    "fetch_shared_collection_by_token",
    "fetch_user_public_collection",
    "generate_rss_xml",
    "generate_sitemap_xml",
    "get_public_expression",
    "get_public_item",
    "get_public_items",
    "get_public_manifestation",
    "get_public_profile",
    "get_public_work",
    "get_shared_collection",
    "global_fresh_feed",
    "lod_bp",
    "public_bp",
    "shared_collection_feed",
    "sitemap",
    "user_collection_feed",
]


class _PublicModuleShim(sys.modules[__name__].__class__):
    """Shim module class to propagate monkeypatched attributes to child modules."""

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name.startswith("__"):
            return
        for submod in (public_items, public_profile, public_rdf):
            if hasattr(submod, name):
                setattr(submod, name, value)


sys.modules[__name__].__class__ = _PublicModuleShim
