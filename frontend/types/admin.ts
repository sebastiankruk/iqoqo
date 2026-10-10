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

/**
 * Single item resolution event in the rolling LOD audit stream.
 */
export interface LODLogEntry {
  timestamp: string;
  manifestation_id: number;
  title: string;
  status: "SUCCESS" | "SKIPPED" | "WARN" | "FAILED" | string;
  links_added: number;
  authorities: string[];
  error?: string | null;
}

/**
 * Authority link counter map.
 */
export interface LODAuthorityCounts {
  dbpedia: number;
  geonames: number;
  wordnet: number;
  [key: string]: number;
}

/**
 * Real-time status payload for an asynchronous LOD batch reconciliation task.
 */
export interface LODReconciliationTaskStatus {
  task_id: string;
  status: "pending" | "processing" | "completed" | "failed" | string;
  state: string;
  percentage: number;
  total: number;
  processed: number;
  total_resolved: number;
  counts: LODAuthorityCounts;
  recent_logs: LODLogEntry[];
  error?: string | null;
}

/**
 * Lifetime Linked Open Data statistics aggregated across the catalog.
 */
export interface LODStats {
  total_manifestations: number;
  linked_manifestations: number;
  unlinked_manifestations: number;
  total_links: number;
  suggested_links?: number;
  by_authority: Record<string, number>;
}

/**
 * Payload parameters for dispatching batch LOD reconciliation.
 */
export interface LODReconciliationTriggerParams {
  manifestation_ids?: number[];
  unlinked_only?: boolean;
  throttle_delay?: number;
}

/**
 * Response received when dispatching batch LOD reconciliation task.
 */
export interface LODReconciliationTriggerResponse {
  task_id: string;
  status: string;
  message: string;
}
