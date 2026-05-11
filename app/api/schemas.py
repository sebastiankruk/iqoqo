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

from pydantic import BaseModel, ConfigDict, Field


class ItemCreateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = Field(default=None, description="The progress status of the item")
    collection_status: str | None = Field(default="available", description="The physical status of the item")
    meta: dict[str, Any] | None = Field(default_factory=dict)


class ItemUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None
    collection_status: str | None = None
    lent_to_user_id: str | None = None
    lent_to_name: str | None = None
    meta: dict[str, Any] | None = None


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


class ManifestationUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    Title: str | None = None
    Authors: list[str] | None = None


class ScanBarcodeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    barcode: str | None = None
    manifestation_id: int | None = None
    format: str | None = None
    collection_status: str | None = "available"
