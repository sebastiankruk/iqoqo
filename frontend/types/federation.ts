// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>
//

export type TrustLevel = "untrusted" | "pending" | "trusted" | "blocked";

export interface FederationInstance {
  id: number;
  domain: string;
  shared_inbox_url: string | null;
  software_name: string | null;
  software_version: string | null;
  last_seen_at: string | null;
  trust_level: TrustLevel;
  created_at: string | null;
}

export interface FederationActivity {
  id: string;
  actor_uri: string;
  activity_type: string;
  object_json: Record<string, unknown> | null;
  target_uri: string | null;
  direction: "inbound" | "outbound";
  delivered_at: string | null;
  retry_count: number;
  status: "queued" | "delivered" | "failed";
  created_at: string | null;
}

export interface FederationConsent {
  user_id: string;
  federated_profile: boolean;
  federated_collection: boolean;
  updated_at: string | null;
}

export interface FederationActivityFilters {
  direction?: "inbound" | "outbound";
  type?: string;
  status?: "queued" | "delivered" | "failed";
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  pages: number;
}
