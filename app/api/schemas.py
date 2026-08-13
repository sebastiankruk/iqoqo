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

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.taxonomy import COLLECTION_STATUSES, PROGRESS_STATUSES


def _validate_uuid_str(v: str | None) -> str | None:
    if v is not None and v.strip() != "":
        try:
            UUID(v)
        except ValueError as err:
            raise ValueError("Invalid UUID format") from err
    return v


class ItemCreateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = Field(default=None, description="The progress status of the item")
    collection_status: str | None = Field(default="available", description="The physical status of the item")
    is_hidden: bool | None = Field(default=False, description="Whether the item is hidden from public profiles")
    tags: list[str] | None = Field(default=None, description="List of tags to apply to the item")
    meta: dict[str, Any] | None = Field(default_factory=dict)
    collection_id: int | None = Field(default=None, description="Optional collection folder to add the item into")
    lent_to_user_id: str | None = Field(default=None, description="The user ID who borrowed the item")
    lent_to_name: str | None = Field(default=None, description="The name of the borrower")

    @model_validator(mode="before")
    @classmethod
    def check_id_not_zero(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key in ("id", "item_id"):
                if key in data and data[key] == 0:
                    raise ValueError("Item identifier cannot be zero.")
        return data

    @field_validator("lent_to_user_id")
    @classmethod
    def validate_lent_to_user_id(cls, v: str | None) -> str | None:
        return _validate_uuid_str(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"Invalid progress status: '{v}'. Must be one of {PROGRESS_STATUSES}")
        return v

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v


class ItemBulkCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifestation_ids: list[int] = Field(..., min_length=1, description="List of manifestation IDs to add")
    status: str | None = Field(default=None, description="The progress status of the items")
    collection_status: str | None = Field(default="available", description="The physical status of the items")
    is_hidden: bool | None = Field(default=False, description="Whether the items are hidden from public profiles")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"Invalid progress status: '{v}'. Must be one of {PROGRESS_STATUSES}")
        return v

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v


class ItemUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None
    collection_status: str | None = None
    lent_to_user_id: str | None = None
    lent_to_name: str | None = None
    is_hidden: bool | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def check_id_not_zero(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key in ("id", "item_id"):
                if key in data and data[key] == 0:
                    raise ValueError("Item identifier cannot be zero.")
        return data

    @field_validator("lent_to_user_id")
    @classmethod
    def validate_lent_to_user_id(cls, v: str | None) -> str | None:
        return _validate_uuid_str(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"Invalid progress status: '{v}'. Must be one of {PROGRESS_STATUSES}")
        return v

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v


class ItemManualCreateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")  # Store all extra fields in meta

    Title: str = Field(..., min_length=1)
    Authors: list[str] | str | None = Field(default_factory=list)
    Format: str | None = "text"
    ISBN: str | None = None
    PublicationDate: str | None = None
    Description: str | None = None
    status: str | None = None
    collection_status: str | None = "available"
    tags: list[str] | None = None
    lent_to_user_id: str | None = Field(default=None, description="The user ID who borrowed the item")
    lent_to_name: str | None = Field(default=None, description="The name of the borrower")

    @field_validator("lent_to_user_id")
    @classmethod
    def validate_lent_to_user_id(cls, v: str | None) -> str | None:
        return _validate_uuid_str(v)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROGRESS_STATUSES:
            raise ValueError(f"Invalid progress status: '{v}'. Must be one of {PROGRESS_STATUSES}")
        return v

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v


class ManifestationUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    Title: str | None = None
    Authors: list[str] | None = None
    genres: list[str] | None = None
    publisher: str | None = None


class ScanBarcodeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    barcode: str | None = Field(default=None, max_length=128)
    manifestation_id: int | None = None
    format: str | None = None
    collection_status: str | None = "available"
    policy: str | None = "inventory"
    lent_to_user_id: str | None = None
    lent_to_name: str | None = None
    meta: dict[str, Any] | None = None

    @field_validator("policy")
    @classmethod
    def validate_policy(cls, v: str | None) -> str | None:
        valid_policies = {"inventory", "wishlist", "catalog"}
        if v is not None and v not in valid_policies:
            raise ValueError(f"Invalid policy: '{v}'. Must be one of {valid_policies}")
        return v

    @field_validator("lent_to_user_id")
    @classmethod
    def validate_lent_to_user_id(cls, v: str | None) -> str | None:
        return _validate_uuid_str(v)

    @field_validator("collection_status")
    @classmethod
    def validate_collection_status(cls, v: str | None) -> str | None:
        if v is not None and v not in COLLECTION_STATUSES:
            raise ValueError(f"Invalid collection status: '{v}'. Must be one of {COLLECTION_STATUSES}")
        return v


class UserCollectionCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    parent_id: int | None = Field(default=None, gt=0, description="Optional ID of the parent collection")


class UserCollectionUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: int | None = Field(default=None, gt=0, description="Optional ID of the parent collection")


class ItemLendSchema(BaseModel):
    """
    Schema for validating item lending payload.

    Enforces the FRBR ontology boundary: virtual items (id <= 0, i.e. UserWorkIntent
    wishlist placeholders) cannot participate in physical loan workflows. Only concrete,
    localized Items with a strictly positive database ID may be lent.
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
    publisher: str | None = Field(default=None, max_length=500)
    publication_date: str | None = None
    format: str | None = Field(default=None, max_length=50, description="Carrier format (e.g. vinyl, cd, bluray)")
    label: str | None = Field(default=None, max_length=500, description="Label or studio name")
    barcode: str | None = Field(default=None, max_length=100, description="UPC/EAN barcode")
    catalog_number: str | None = Field(default=None, max_length=100, description="Label catalog number")
    meta: dict[str, Any] | None = None


class ItemCollectionLinkSchema(BaseModel):
    """Schema for linking an item to a named collection."""

    model_config = ConfigDict(extra="forbid")

    collection_id: int = Field(..., gt=0, description="ID of the collection to link the item to")
