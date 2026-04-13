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

# Auto-generated permissions (fallback copy)

from enum import Enum


class ItemPermissions(Enum):
    REFETCH_METADATA = "refetch:metadata"
    REGENERATE_COVER = "regenerate:cover"
    DELETE_ITEM = "delete:item"
    DELETE_MANIFESTATION = "delete:manifestation"
    LLM_GENERATE_COVER = "llm_generate:cover"
    LLM_GENERATE_METADATA = "llm_generate:metadata"
    LLM_GENERATE_CLOUD = "llm_generate:cloud"
    UPLOAD_COVER = "upload:cover"
    CONFIG_EXTERNAL_APIS = "config:external_apis"
    CONFIG_FEDERATION = "config:federation"
    CONFIG_AFFILIATE = "config:affiliate"
    CONFIG_INTERNAL = "config:internal"
    READ_USERS = "read:users"
    WRITE_USERS = "write:users"
    READ_ROLES = "read:roles"
    WRITE_ROLES = "write:roles"
