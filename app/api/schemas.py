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
"""Pydantic schemas for API payload validation."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.taxonomy import COLLECTION_STATUSES, PROGRESS_STATUSES
from app.db.core import ITEM_VISIBILITIES

SHARED_VISIBILITY_SCOPES = ("public_only", "friends_and_public", "all")


def _validate_uuid_str(v: str | None) -> str | None:
    if v is not None and v.strip() != "":
        try:
            UUID(v)
        except ValueError as err:
            raise ValueError("Invalid UUID format") from err
    return v


class ItemCreateSchema(BaseModel):
    """Request body for adding a new physical item to the library.

    ``extra="allow"`` because the API accepts provider-specific fields that are
    preserved into ``meta`` rather than rejected: a client that round-trips a
    record from another system should not lose fields this schema has never
    heard of.
    """

    model_config = ConfigDict(extra="allow")

    status: str | None = Field(default=None, description="The progress status of the item")
    collection_status: str | None = Field(default="available", description="The physical status of the item")
    visibility: str | None = Field(default=None, description="The visibility tier of the item ('public', 'friends_only', 'private')")
    is_hidden: bool | None = Field(default=None, description="Whether the item is hidden from public profiles")
    cumulative_issue_number: int | None = Field(default=None, ge=1)
    publication_year: int | None = Field(default=None, ge=1400, le=2100)
    publication_month: int | None = Field(default=None, ge=1, le=12)
    tags: list[str] | None = Field(default=None, description="List of tags to apply to the item")
    meta: dict[str, Any] | None = Field(default_factory=dict)
    collection_id: int | None = Field(default=None, description="Optional collection folder to add the item into")
    manifestation_id: int | None = Field(default=None, description="The manifestation ID to shelve an item under")
    local_barcode: str | None = Field(default=None, max_length=64, description="Local barcode or inventory asset tag")
    lent_to_user_id: str | None = Field(default=None, description="The user ID who borrowed the item")
    lent_to_name: str | None = Field(default=None, description="The name of the borrower")

    @model_validator(mode="before")
    @classmethod
    def check_id_positive(cls, data: Any) -> Any:
        """Reject a non-positive ``id``/``item_id`` before field validation.

        Runs in ``before`` mode so the check sees the raw payload. A
        zero-or-negative primary key would otherwise be accepted here and fail
        later as a foreign-key error, far from the request that caused it.
        """
        if isinstance(data, dict):
            for key in ("id", "item_id"):
                if key in data and data[key] is not None and data[key] <= 0:
                    raise ValueError("Item identifier must be a positive integer.")
        return data

    @field_validator("lent_to_user_id")
    @classmethod
    def validate_lent_to_user_id(cls, v: str | None) -> str | None:
        """Ensure the borrower id is a well-formed UUID, or absent."""
        return _validate_uuid_str(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Constrain the progress status to the controlled vocabulary."""
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"Invalid progress status: '{v}'. Must be one of {PROGRESS_STATUSES}")
        return v

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        """Constrain the physical status to the controlled vocabulary."""
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str | None) -> str | None:
        """Constrain item visibility to controlled vocabulary."""
        if v is not None and v not in ITEM_VISIBILITIES:
            raise ValueError(f"Invalid visibility: '{v}'. Must be one of {ITEM_VISIBILITIES}")
        return v


class ItemBulkCreateSchema(BaseModel):
    """Request body for adding several manifestations to the library at once.

    ``extra="forbid"`` because a bulk operation with silently ignored fields
    would apply a partial change while appearing to apply the whole one.
    """

    model_config = ConfigDict(extra="forbid")

    manifestation_ids: list[int] = Field(..., min_length=1, description="List of manifestation IDs to add")
    status: str | None = Field(default=None, description="The progress status of the items")
    collection_status: str | None = Field(default="available", description="The physical status of the items")
    visibility: str | None = Field(default=None, description="The visibility tier of the items ('public', 'friends_only', 'private')")
    is_hidden: bool | None = Field(default=None, description="Whether the items are hidden from public profiles")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Constrain the progress status to the controlled vocabulary."""
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"Invalid progress status: '{v}'. Must be one of {PROGRESS_STATUSES}")
        return v

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        """Constrain the physical status to the controlled vocabulary."""
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str | None) -> str | None:
        """Constrain item visibility to controlled vocabulary."""
        if v is not None and v not in ITEM_VISIBILITIES:
            raise ValueError(f"Invalid visibility: '{v}'. Must be one of {ITEM_VISIBILITIES}")
        return v


class ItemUpdateSchema(BaseModel):
    """Request body for editing an existing item.

    Every field is optional: an absent field means "unchanged", so a partial
    edit does not require resending the whole record.
    """

    model_config = ConfigDict(extra="allow")

    status: str | None = None
    collection_status: str | None = None
    condition: str | None = None
    local_barcode: str | None = Field(default=None, max_length=64, description="Local barcode or inventory asset tag")
    lent_to_user_id: str | None = None
    lent_to_name: str | None = None
    visibility: str | None = None
    is_hidden: bool | None = None
    tags: list[str] | None = None
    map_insert_present: bool | None = None
    build_status: Literal["sealed", "built", "incomplete", "parted_out"] | None = None
    missing_pieces_count: int | None = Field(default=None, ge=0)
    instructions_included: bool | None = None
    box_condition: str | None = None
    meta: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def check_id_positive(cls, data: Any) -> Any:
        """Reject a non-positive ``id``/``item_id`` in an update payload.

        An update that sets the primary key to 0 or a negative value is
        rejected here rather than becoming a constraint violation on flush.
        """
        if isinstance(data, dict):
            for key in ("id", "item_id"):
                if key in data and data[key] is not None and data[key] <= 0:
                    raise ValueError("Item identifier must be a positive integer.")
        return data

    @field_validator("lent_to_user_id")
    @classmethod
    def validate_lent_to_user_id(cls, v: str | None) -> str | None:
        """Ensure the borrower id is a well-formed UUID, or absent."""
        return _validate_uuid_str(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Constrain the progress status to the controlled vocabulary."""
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"Invalid progress status: '{v}'. Must be one of {PROGRESS_STATUSES}")
        return v

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        """Constrain the physical status to the controlled vocabulary."""
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str | None) -> str | None:
        """Constrain item visibility to controlled vocabulary."""
        if v is not None and v not in ITEM_VISIBILITIES:
            raise ValueError(f"Invalid visibility: '{v}'. Must be one of {ITEM_VISIBILITIES}")
        return v


class BulkItemVisibilitySchema(BaseModel):
    """Request body for updating visibility across multiple owned physical items."""

    model_config = ConfigDict(extra="forbid")

    item_ids: list[int] = Field(min_length=1, max_length=100, description="List of owned physical item IDs (1..100)")
    visibility: str = Field(..., description="Target visibility tier ('public', 'friends_only', 'private')")

    @field_validator("item_ids")
    @classmethod
    def validate_item_ids(cls, v: list[int]) -> list[int]:
        """Ensure all item identifiers are positive integers."""
        if any(item_id <= 0 for item_id in v):
            raise ValueError("All item_ids must be positive integers.")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str) -> str:
        """Normalize 'hidden' alias and constrain visibility to controlled tiers."""
        normalized = "private" if str(v).strip().lower() == "hidden" else str(v).strip().lower()
        if normalized not in ("public", "friends_only", "private"):
            raise ValueError("Invalid visibility. Must be one of ('public', 'friends_only', 'private')")
        return normalized


class ItemManualCreateSchema(BaseModel):
    """Request body for creating an item by hand, without a scanned barcode.

    The capitalised field names mirror the provider payload format used by the
    import tooling, so the same body can be fed from a file or a form.
    """

    model_config = ConfigDict(extra="allow")  # Store all extra fields in meta

    Title: str = Field(..., min_length=1)
    Authors: list[str] | str | None = Field(default_factory=list)
    Format: str | None = "text"
    ISBN: str | None = None
    PublicationDate: str | None = None
    Description: str | None = None
    status: str | None = None
    collection_status: str | None = "available"
    local_barcode: str | None = Field(default=None, max_length=64, description="Local barcode or inventory asset tag")
    tags: list[str] | None = None
    lent_to_user_id: str | None = Field(default=None, description="The user ID who borrowed the item")
    lent_to_name: str | None = Field(default=None, description="The name of the borrower")
    visibility: str | None = Field(default=None, description="The visibility tier of the item ('public', 'friends_only', 'private')")
    is_hidden: bool | None = Field(default=None, description="Whether the item is hidden from public profiles")
    cumulative_issue_number: int | None = Field(default=None, ge=1)
    publication_year: int | None = Field(default=None, ge=1400, le=2100)
    publication_month: int | None = Field(default=None, ge=1, le=12)

    @field_validator("lent_to_user_id")
    @classmethod
    def validate_lent_to_user_id(cls, v: str | None) -> str | None:
        """Ensure the borrower id is a well-formed UUID, or absent."""
        return _validate_uuid_str(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Constrain the progress status to the controlled vocabulary."""
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"Invalid progress status: '{v}'. Must be one of {PROGRESS_STATUSES}")
        return v

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        """Constrain the physical status to the controlled vocabulary."""
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str | None) -> str | None:
        """Constrain item visibility to controlled vocabulary."""
        if v is not None and v not in ITEM_VISIBILITIES:
            raise ValueError(f"Invalid visibility: '{v}'. Must be one of {ITEM_VISIBILITIES}")
        return v


class ManifestationUpdateSchema(BaseModel):
    """Request body for editing manifestation-level bibliographic metadata.

    The title and author changes cascade to the parent Work and sibling
    Expressions; see the admin API for the propagation rules.
    """

    model_config = ConfigDict(extra="allow")

    Title: str | None = None
    Authors: list[str] | None = None
    genres: list[str] | None = None
    publisher: str | None = Field(default=None, max_length=255)
    format_type: str | None = Field(default=None, max_length=50)
    format: str | None = Field(default=None, max_length=50)
    isbn13: str | None = Field(default=None, max_length=20)
    issue_number: str | None = Field(default=None, max_length=32)
    cumulative_issue_number: int | None = Field(default=None, ge=1)
    volume: str | None = Field(default=None, max_length=32)
    publication_year: int | None = Field(default=None, ge=1400, le=2100)
    publication_month: int | None = Field(default=None, ge=1, le=12)
    ean_addon: str | None = Field(default=None, max_length=8)
    full_barcode: str | None = Field(default=None, max_length=20)
    cover_headline: str | None = Field(default=None, max_length=500)


class ScanBarcodeSchema(BaseModel):
    """Request body for a barcode scan.

    ``policy`` decides what a scan does beyond resolving a manifestation:
    ``inventory`` files a physical item, ``wishlist`` records intent to buy,
    and the ``catalog`` variants only refresh metadata.
    """

    model_config = ConfigDict(extra="forbid")

    barcode: str | None = Field(default=None, max_length=128)
    manifestation_id: int | None = None
    format: str | None = None
    collection_status: str | None = "available"
    policy: str | None = "inventory"
    lent_to_user_id: str | None = None
    lent_to_name: str | None = None
    meta: dict[str, Any] | None = None
    visibility: str | None = None
    is_hidden: bool | None = None
    is_public: bool | None = None

    @field_validator("policy")
    @classmethod
    def validate_policy(cls, v: str | None) -> str | None:
        """Constrain the scan policy to the supported set."""
        valid_policies = {"inventory", "wishlist", "catalog", "catalog_only"}
        if v is not None and v not in valid_policies:
            raise ValueError(f"Invalid policy: '{v}'. Must be one of {valid_policies}")
        return v

    @field_validator("lent_to_user_id")
    @classmethod
    def validate_lent_to_user_id(cls, v: str | None) -> str | None:
        """Ensure the borrower id is a well-formed UUID, or absent."""
        return _validate_uuid_str(v)

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        """Constrain the physical status to the controlled vocabulary."""
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, v: str | None) -> str | None:
        """Constrain item visibility to controlled vocabulary."""
        if v is not None and v not in ITEM_VISIBILITIES:
            raise ValueError(f"Invalid visibility: '{v}'. Must be one of {ITEM_VISIBILITIES}")
        return v


class UserCollectionCreateSchema(BaseModel):
    """Request body for creating a user collection folder."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    parent_id: int | None = Field(default=None, gt=0, description="Optional ID of the parent collection")


class UserCollectionUpdateSchema(BaseModel):
    """Request body for renaming or re-parenting a user collection folder.

    ``parent_id`` may be set to null to move a collection to the root; cycle
    detection happens server-side, since it needs the whole tree.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: int | None = Field(default=None, gt=0, description="Optional ID of the parent collection")


class ItemLendSchema(BaseModel):
    """
    Schema for validating item lending payload.

    Only physical Items with a strictly positive database ID may be lent.
    Wishlist entries are managed through the dedicated ``/api/wishlist`` blueprint.
    """

    model_config = ConfigDict(extra="forbid")

    item_id: int = Field(
        ge=1,
        description="The ID of the physical item to lend. Must be strictly greater than 0.",
    )
    borrower_id: str | None = Field(
        default=None,
        description="The UUID of the borrower user, if known.",
    )
    borrower_name: str | None = Field(
        default=None,
        description="The display name of the borrower.",
    )
    notes: str | None = Field(default=None, description="Optional notes for the loan request.")

    @field_validator("borrower_id")
    @classmethod
    def validate_borrower_id(cls, v: str | None) -> str | None:
        """Ensure the borrower id is a well-formed UUID, or absent."""
        return _validate_uuid_str(v)


class ExpressionUpdateSchema(BaseModel):
    """Schema for expression metadata update via FRBR admin editor."""

    model_config = ConfigDict(extra="allow")

    work_id: int | None = None
    content_type: str | None = None
    language: str | None = None
    kind: str | None = Field(default=None, max_length=50, description="Expression kind (e.g. live_performance)")
    meta: dict[str, Any] | None = None


class ManifestationFrbrUpdateSchema(BaseModel):
    """Schema for manifestation FRBR admin editor updates with promoted relational fields."""

    model_config = ConfigDict(extra="allow")

    expression_id: int | None = None
    isbn13: str | None = Field(default=None, max_length=20)
    upc: str | None = Field(default=None, max_length=20)
    ean: str | None = Field(default=None, max_length=20)
    publisher: str | None = Field(default=None, max_length=255)
    publication_date: str | None = None
    format_type: str | None = Field(default=None, max_length=50, description="Carrier format type (e.g. hardcover, paperback, vinyl)")
    format: str | None = Field(default=None, max_length=50, description="Carrier format (e.g. vinyl, cd, bluray)")
    label: str | None = Field(default=None, max_length=500, description="Label or studio name")
    barcode: str | None = Field(default=None, max_length=100, description="UPC/EAN barcode")
    catalog_number: str | None = Field(default=None, max_length=100, description="Label catalog number")
    meta: dict[str, Any] | None = None


class ItemCollectionLinkSchema(BaseModel):
    """Schema for linking an item to a named collection."""

    model_config = ConfigDict(extra="forbid")

    collection_id: int = Field(..., gt=0, description="ID of the collection to link the item to")


class FeedbackUpdateSchema(BaseModel):
    """Schema for updating a feedback ticket."""

    model_config = ConfigDict(extra="forbid")

    status: str | None = Field(default=None, description="Updated status of the ticket")
    feedback_type: str | None = Field(default=None, description="Updated feedback type")
    description: str | None = Field(default=None, min_length=1, max_length=20000, description="Updated description")
    comment: str | None = Field(default=None, description="Comment text to add to the ticket")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Constrain a ticket status to the controlled vocabulary."""
        if v is not None and v not in {"new", "accepted", "in_progress", "in_validation", "closed"}:
            raise ValueError(f"Invalid status: {v}. Must be one of new, accepted, in_progress, in_validation, closed")
        return v

    @field_validator("feedback_type")
    @classmethod
    def validate_feedback_type(cls, v: str | None) -> str | None:
        """Constrain the feedback type to ``feature_request`` or ``bug``."""
        if v is not None and v not in {"feature_request", "bug"}:
            raise ValueError(f"Invalid feedback_type: {v}. Must be one of feature_request, bug")
        return v

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "FeedbackUpdateSchema":
        """Reject an update that changes nothing.

        An all-absent payload would otherwise return 200 having written
        nothing, which reads as a successful edit to the client.
        """
        if self.status is None and self.feedback_type is None and self.description is None and self.comment is None:
            raise ValueError("No valid fields provided for update")
        return self


# ---------------------------------------------------------------------------
# FRBR Relation Management Schemas
# ---------------------------------------------------------------------------


class FrbrReassignSchema(BaseModel):
    """Schema for reassigning an entity's parent in the FRBR hierarchy."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(..., description="The entity type to reassign (expression, manifestation, or item)")
    entity_id: int = Field(..., gt=0, description="The ID of the entity to reassign")
    new_parent_id: int = Field(..., gt=0, description="The ID of the new parent entity")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Restrict reassignment to entity types that can have a new parent."""
        allowed = {"expression", "manifestation", "item"}
        if v not in allowed:
            raise ValueError(f"Invalid entity_type for reassign: {v!r}. Must be one of {sorted(allowed)}")
        return v


class FrbrMergeSchema(BaseModel):
    """Schema for merging two entities at the same FRBR level."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(..., description="The entity type to merge (work, expression, or manifestation)")
    source_id: int = Field(..., gt=0, description="The ID of the source entity (to be deleted)")
    target_id: int = Field(..., gt=0, description="The ID of the target entity (to be kept)")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Restrict merging to entity types that exist at this level.

        ``work`` is included here but not in the reassign set: a Work is the
        root of the FRBR hierarchy and cannot be re-parented, but it can be the
        target of a merge.
        """
        allowed = {"work", "expression", "manifestation"}
        if v not in allowed:
            raise ValueError(f"Invalid entity_type for merge: {v!r}. Must be one of {sorted(allowed)}")
        return v

    @model_validator(mode="after")
    def check_different_ids(self) -> "FrbrMergeSchema":
        """Reject a merge whose source and target are the same row.

        Merging a row into itself would delete it and then re-point every
        reference at nothing.
        """
        if self.source_id == self.target_id:
            raise ValueError("source_id and target_id must be different")
        return self


class FrbrSplitSchema(BaseModel):
    """Schema for splitting children from an entity into a new sibling entity."""

    model_config = ConfigDict(extra="forbid")

    entity_type: str = Field(..., description="The entity type to split (work, expression, or manifestation)")
    source_id: int = Field(..., gt=0, description="The ID of the source entity")
    child_ids: list[int] = Field(..., min_length=1, description="IDs of children to move to the new entity")
    new_entity_attrs: dict[str, Any] = Field(..., description="Attributes for the new entity")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Restrict splitting to entity types that own children."""
        allowed = {"work", "expression", "manifestation"}
        if v not in allowed:
            raise ValueError(f"Invalid entity_type for split: {v!r}. Must be one of {sorted(allowed)}")
        return v

    @field_validator("child_ids")
    @classmethod
    def validate_child_ids(cls, v: list[int]) -> list[int]:
        """Require every child id to be a positive integer."""
        if any(cid <= 0 for cid in v):
            raise ValueError("All child_ids must be positive integers")
        return v


class ReadingSessionCreateSchema(BaseModel):
    """Request body for logging a reading session on an owned physical item."""

    model_config = ConfigDict(extra="forbid")

    duration_minutes: int = Field(..., ge=1, le=1440, description="Active reading session duration in minutes (1-1440)")
    pages_read: int | None = Field(default=None, ge=1, le=5000, description="Optional number of pages read in this session")
    note: str | None = Field(default=None, max_length=280, description="Optional short session note")

    @field_validator("note")
    @classmethod
    def normalize_note(cls, v: str | None) -> str | None:
        """Trim surrounding whitespace and normalize empty notes to None."""
        if v is None:
            return None
        stripped = v.strip()
        return stripped if stripped else None


class SharedCollectionCreateSchema(BaseModel):
    """Request body for creating a shared collection link with configurable visibility scope."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    filters: dict[str, Any] = Field(default_factory=dict)
    visibility_scope: str | None = Field(
        default=None,
        description="Visibility scope for the generated token ('public_only', 'friends_and_public', 'all')",
    )
    expires_in_days: int | None = Field(default=None, description="Optional expiry duration in days (1-365)")

    @field_validator("visibility_scope")
    @classmethod
    def validate_visibility_scope(cls, v: str | None) -> str | None:
        """Validate top-level visibility_scope against supported shared collection scopes."""
        if v is None:
            return None
        if not isinstance(v, str) or v.strip() not in SHARED_VISIBILITY_SCOPES:
            raise ValueError(f"Invalid visibility_scope '{v}'. Must be one of {SHARED_VISIBILITY_SCOPES}")
        return v.strip()

    @field_validator("filters", mode="before")
    @classmethod
    def normalize_filters(cls, v: Any) -> dict[str, Any]:
        """Ensure filters is a dict and validate filters.visibility_scope if supplied."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("'filters' must be a JSON object")
        copied = dict(v)
        nested_scope = copied.get("visibility_scope")
        if nested_scope is not None:
            if not isinstance(nested_scope, str) or nested_scope.strip() not in SHARED_VISIBILITY_SCOPES:
                raise ValueError(f"Invalid filters.visibility_scope '{nested_scope}'. Must be one of {SHARED_VISIBILITY_SCOPES}")
            copied["visibility_scope"] = nested_scope.strip()

        from app.core.format_normalizer import FormatNormalizer
        from app.core.taxonomy import FORMAT_ALIAS_TO_CATEGORY, MediaCategory, MediaFormat

        valid_categories = set(MediaCategory.ALL)
        for cat_key in ("tags", "category"):
            if cat_key in copied and copied[cat_key] is not None:
                raw_cats = copied[cat_key]
                cat_list = raw_cats if isinstance(raw_cats, list) else [raw_cats]
                norm_cats: list[str] = []
                for item in cat_list:
                    if not isinstance(item, str):
                        raise ValueError(f"Invalid category filter value: {item!r}")
                    cleaned = item.strip().lower()
                    if not cleaned:
                        continue
                    mapped = FORMAT_ALIAS_TO_CATEGORY.get(cleaned, cleaned)
                    if mapped not in valid_categories:
                        raise ValueError(f"Invalid category '{item}' in filters.{cat_key}")
                    if mapped not in norm_cats:
                        norm_cats.append(mapped)
                copied[cat_key] = norm_cats

        valid_formats = set(MediaFormat.ALL)
        for fmt_key in ("format", "formats"):
            if fmt_key in copied and copied[fmt_key] is not None:
                raw_fmts = copied[fmt_key]
                fmt_list = raw_fmts if isinstance(raw_fmts, list) else [raw_fmts]
                norm_fmts: list[str] = []
                for item in fmt_list:
                    if not isinstance(item, str):
                        raise ValueError(f"Invalid format filter value: {item!r}")
                    cleaned = item.strip().lower()
                    if not cleaned:
                        continue
                    if cleaned in valid_formats:
                        resolved = cleaned
                    else:
                        FormatNormalizer._load_mappings()
                        if cleaned in FormatNormalizer._mappings:
                            resolved = FormatNormalizer._mappings[cleaned]
                        elif cleaned in FORMAT_ALIAS_TO_CATEGORY:
                            resolved = FormatNormalizer.normalize(cleaned)
                        else:
                            raise ValueError(f"Invalid format '{item}' in filters.{fmt_key}")
                    if resolved not in norm_fmts:
                        norm_fmts.append(resolved)
                copied[fmt_key] = norm_fmts

        return copied

    @field_validator("expires_in_days", mode="before")
    @classmethod
    def validate_expires_in_days(cls, v: Any) -> int | None:
        """Validate expires_in_days is an integer between 1 and 365."""
        if v is None:
            return None
        if isinstance(v, bool):
            raise ValueError("'expires_in_days' must be an integer")
        try:
            days = int(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("'expires_in_days' must be an integer") from exc
        if not 1 <= days <= 365:
            raise ValueError("'expires_in_days' must be between 1 and 365")
        return days

    def resolved_filters(self) -> dict[str, Any]:
        """Return filters dict with canonical 'visibility_scope' guaranteed populated."""
        merged = dict(self.filters or {})
        effective_scope = self.visibility_scope or merged.get("visibility_scope") or "public_only"
        merged["visibility_scope"] = effective_scope
        return merged


class WorkLinkScanRequest(BaseModel):
    """Pydantic schema for triggering a cross-media Work link scan."""

    model_config = ConfigDict(extra="forbid")

    engine: str = "heuristic"
    threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    limit: int | None = Field(default=None, ge=1, le=5000)
    dry_run: bool = False


class WorkLinkAcceptRequest(BaseModel):
    """Pydantic schema for accepting a pending cross-media WorkLinkCandidate."""

    model_config = ConfigDict(extra="forbid")

    relation_type: str | None = None
    source_work_id: int | None = Field(default=None, ge=1)
    target_work_id: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=2000)


class WorkLinkCreateRequest(BaseModel):
    """Pydantic schema for manually creating a confirmed WorkRelation."""

    model_config = ConfigDict(extra="forbid")

    source_work_id: int = Field(ge=1)
    target_work_id: int = Field(ge=1)
    relation_type: str = "is_adaptation_of"
    notes: str | None = Field(default=None, max_length=2000)
