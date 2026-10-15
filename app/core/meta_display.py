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
"""Manifestation metadata display projection table and builder.

Provides the canonical backend declaration of metadata fields rendered by the UI,
mapping provider and OCR metadata to an ordered display projection. This ensures
every logical field renders exactly once and eliminates client-side suppression
drift.
"""

from dataclasses import dataclass
from typing import Any

# Structural column keys excluded from display (matched case-insensitively)
EXCLUDED_STRUCTURAL_KEYS = {
    "id",
    "manifestation_id",
    "cover_url",
    "image",
    "cover_status",
    "cover",
}

# Values considered empty / placeholder in UI display
DISALLOWED_VALUES = {"unknown", "n/a", "none", ""}


@dataclass(frozen=True)
class DisplayFieldDef:
    """Declaration of a logical metadata field rendered in the interface."""

    field: str
    spellings: tuple[str, ...]
    section: str
    label: str


# Canonical field vocabulary matching frontend/lib/meta.ts FIELD_CHAINS
DISPLAY_FIELD_DEFINITIONS: dict[str, DisplayFieldDef] = {
    "format": DisplayFieldDef(
        field="format",
        spellings=("format", "Format"),
        section="format",
        label="Media Format",
    ),
    "year": DisplayFieldDef(
        field="year",
        spellings=("year", "Year"),
        section="header",
        label="Year",
    ),
    "title": DisplayFieldDef(
        field="title",
        spellings=("title", "Title"),
        section="header",
        label="Title",
    ),
    "author": DisplayFieldDef(
        field="author",
        spellings=("author", "authors", "Author", "Authors"),
        section="header",
        label="Author",
    ),
    "authors": DisplayFieldDef(
        field="authors",
        spellings=("authors", "author", "Authors", "Author"),
        section="header",
        label="Authors",
    ),
    "description": DisplayFieldDef(
        field="description",
        spellings=("description", "Description"),
        section="description",
        label="Description",
    ),
    "categories": DisplayFieldDef(
        field="categories",
        spellings=("categories", "Categories"),
        section="categories",
        label="Categories",
    ),
    "pages": DisplayFieldDef(
        field="pages",
        spellings=("pages", "Pages"),
        section="header",
        label="Pages",
    ),
    "tracks": DisplayFieldDef(
        field="tracks",
        spellings=("tracks", "Tracks"),
        section="release_information",
        label="Tracks",
    ),
    "publisher": DisplayFieldDef(
        field="publisher",
        spellings=("publisher", "label", "Publisher"),
        section="release_information",
        label="Label / Publisher",
    ),
    "subtitle": DisplayFieldDef(
        field="subtitle",
        spellings=("subtitle", "Subtitle"),
        section="header",
        label="Subtitle",
    ),
}

# Explicit precedence orders for sections (design decision 4)
# ExtendedMetadata prioritizes label over publisher
EXTENDED_METADATA_LABEL_PUBLISHER_PRECEDENCE: tuple[str, ...] = ("label", "publisher", "Label", "Publisher")
# ItemHeader prioritizes publisher over label
ITEM_HEADER_PUBLISHER_PRECEDENCE: tuple[str, ...] = ("publisher", "label", "Publisher")

# All spellings declared across canonical fields
ALL_DECLARED_SPELLINGS: set[str] = {spelling for defn in DISPLAY_FIELD_DEFINITIONS.values() for spelling in defn.spellings}

# Additional keys rendered in dedicated sections or structural display
ADDITIONAL_SECTION_KEYS: set[str] = {
    # Release Information (audio)
    "label",
    "Label",
    "catalog_number",
    "catalog_no",
    "cat_no",
    "CatalogNumber",
    "matrix_number",
    "MatrixNumber",
    "pressing_number",
    "PressingNumber",
    "disc_count",
    "DiscCount",
    "track_list",
    # Video
    "cast",
    "Cast",
    "directors",
    "Director",
    "runtime",
    "Runtime",
    # Board Game
    "min_players",
    "MinPlayers",
    "max_players",
    "MaxPlayers",
    "playing_time",
    "playtime",
    "PlayTime",
    "min_playtime",
    "max_playtime",
    "mechanics",
    "Mechanics",
    # Puzzle
    "piece_count",
    "dimensions",
    "artist",
    "manufacturer",
    "puzzle_type",
    # Identifiers & Covers handled structurally
    "barcode",
    "Barcode",
    "isbn",
    "ISBN",
    "cover_status",
    "cover_source",
    "cover_url",
    "cover_status_updated_at",
    "local_cover",
    "tags",
    "additional_images",
    "imageLinks",
    "data_source",
}

# All keys that are rendered in a dedicated surface and should be omitted from Additional Details
ALL_RENDERED_OR_STRUCTURAL_KEYS: set[str] = ALL_DECLARED_SPELLINGS | ADDITIONAL_SECTION_KEYS | {k.lower() for k in EXCLUDED_STRUCTURAL_KEYS}
ALL_RENDERED_OR_STRUCTURAL_KEYS_LOWER: set[str] = {k.lower() for k in ALL_RENDERED_OR_STRUCTURAL_KEYS}


def read_first_present_value(meta: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Read the first present non-empty value matching the key precedence chain."""
    for key in keys:
        if key in meta:
            val = meta[key]
            if is_valid_display_value(val):
                return val
    return None


def is_valid_display_value(value: Any) -> bool:
    """Check if a metadata value is non-empty and valid for UI display."""
    if value is None:
        return False
    if isinstance(value, str):
        val_clean = value.strip().lower()
        if not val_clean or val_clean in DISALLOWED_VALUES:
            return False
    return True


def is_primitive_value(value: Any) -> bool:
    """Check if a value is a displayable primitive (string, number, boolean)."""
    return isinstance(value, (str, int, float, bool))


def build_display_projection(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Build an ordered display projection from raw manifestation metadata.

    Applies server-side normalization and value-level display rules so that:
    1. Each logical field is extracted with its canonical label and section.
    2. Fields rendered in primary sections are not duplicated in additional details.
    3. Empty, unknown, n/a, or non-primitive object values are filtered out.
    4. Unrecognized primitive keys appear in additional_details.
    """
    if not isinstance(meta, dict) or not meta:
        return {
            "sections": {},
            "fields": {},
            "additional_details": [],
        }

    sections: dict[str, Any] = {}
    fields: dict[str, Any] = {}

    # 1. Format section
    fmt_val = read_first_present_value(meta, DISPLAY_FIELD_DEFINITIONS["format"].spellings)
    if fmt_val is not None:
        sections["format"] = fmt_val
        fields["format"] = fmt_val

    # 2. Description section
    desc_val = read_first_present_value(meta, DISPLAY_FIELD_DEFINITIONS["description"].spellings)
    if desc_val is not None:
        sections["description"] = desc_val
        fields["description"] = desc_val

    # 3. Categories section
    cat_val = read_first_present_value(meta, DISPLAY_FIELD_DEFINITIONS["categories"].spellings)
    if cat_val is not None:
        if isinstance(cat_val, list):
            sections["categories"] = [str(c) for c in cat_val if is_valid_display_value(c)]
        elif isinstance(cat_val, str) and is_valid_display_value(cat_val):
            sections["categories"] = [cat_val]
        fields["categories"] = sections.get("categories", [])

    # 4. Release Information: Label / Publisher with explicit precedence
    label_pub_val = read_first_present_value(meta, EXTENDED_METADATA_LABEL_PUBLISHER_PRECEDENCE)
    header_pub_val = read_first_present_value(meta, ITEM_HEADER_PUBLISHER_PRECEDENCE)
    if label_pub_val is not None:
        sections["label_publisher"] = label_pub_val
        fields["publisher"] = label_pub_val
    elif header_pub_val is not None:
        fields["publisher"] = header_pub_val

    # 5. Additional Details (catch-all for primitive values not rendered in dedicated sections)
    additional_details: list[dict[str, Any]] = []
    for raw_key, raw_val in meta.items():
        if not isinstance(raw_key, str):
            continue

        # Exclude internal / provenance keys starting with '_'
        if raw_key.startswith("_"):
            continue

        raw_key_lower = raw_key.lower()

        # Exclude structural columns
        if raw_key_lower in EXCLUDED_STRUCTURAL_KEYS:
            continue

        # Exclude keys rendered in dedicated sections or declared in vocabulary
        if raw_key in ALL_RENDERED_OR_STRUCTURAL_KEYS or raw_key_lower in ALL_RENDERED_OR_STRUCTURAL_KEYS_LOWER:
            continue

        # Value-level filtering
        if not is_valid_display_value(raw_val) or not is_primitive_value(raw_val):
            continue

        additional_details.append(
            {
                "key": raw_key,
                "label": raw_key.replace("_", " "),
                "value": raw_val,
            }
        )

    return {
        "sections": sections,
        "fields": fields,
        "additional_details": additional_details,
    }
