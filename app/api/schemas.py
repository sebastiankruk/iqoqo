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
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ItemCreateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = Field(default=None, description="The progress status of the item")
    collection_status: Optional[str] = Field(default="available", description="The physical status of the item")
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ItemUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = None
    collection_status: Optional[str] = None
    lent_to_user_id: Optional[str] = None
    lent_to_name: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class ItemManualCreateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")  # Store all extra fields in meta

    Title: str = Field(..., min_length=1)
    Authors: Optional[List[str] | str] = Field(default_factory=list)
    Format: Optional[str] = "text"
    ISBN: Optional[Optional[str]] = None
    PublicationDate: Optional[Optional[str]] = None
    Description: Optional[Optional[str]] = None
    status: Optional[str] = None
    collection_status: Optional[str] = "available"


class ManifestationUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    Title: Optional[str] = None
    Authors: Optional[List[str]] = None


class ScanBarcodeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    barcode: Optional[str] = None
    manifestation_id: Optional[int] = None
    format: Optional[str] = None
    collection_status: Optional[str] = "available"
