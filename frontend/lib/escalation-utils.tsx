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

import type { EscalationRequest } from "@/types/frbr";

/**
 * Get target entity link path for an escalation request.
 *
 * @param esc - Escalation request object.
 * @returns Target URL path or null if no target entity is set.
 */
export function getTargetHref(esc: EscalationRequest): string | null {
  if (esc.manifestation_id) return `/manifestation/${esc.manifestation_id}`;
  if (esc.work_id) return `/collection?work_id=${esc.work_id}`;
  if (esc.item_id) return `/item/${esc.item_id}`;
  return null;
}

/**
 * Get target entity formatted label string.
 *
 * @param esc - Escalation request object.
 * @returns Formatted target label string.
 */
export function getTargetLabel(esc: EscalationRequest): string {
  if (esc.manifestation_id) return `Manifestation #${esc.manifestation_id}`;
  if (esc.work_id) return `Work #${esc.work_id}`;
  if (esc.expression_id) return `Expression #${esc.expression_id}`;
  if (esc.item_id) return `Item #${esc.item_id}`;
  return "FRBR Entity";
}
