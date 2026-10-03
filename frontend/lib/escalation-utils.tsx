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
 * Get target entity link path for an escalation request (public view).
 *
 * @param esc - Escalation request object.
 * @returns Target URL path or null if no target entity is set.
 */
export function getTargetHref(esc: EscalationRequest): string | null {
  if (esc.manifestation_id) return `/manifestation/${esc.manifestation_id}`;
  // An Expression escalation stores `expression_id` with `work_id` NULL, because
  // `chk_escalation_target_exactly_one` allows at most one target and
  // `create_escalation_request` writes only `f"{level}_id"`. The previous
  // `if (esc.expression_id && esc.work_id)` therefore never matched for an
  // Expression, and fell through to `null` -- so every Expression escalation
  // rendered as unclickable text. `work_id` stays in the condition for the
  // legacy shape where both were set, which /work/[id] can anchor into.
  if (esc.expression_id) return `/expression/${esc.expression_id}`;
  if (esc.work_id) return `/collection?work_id=${esc.work_id}`;
  if (esc.item_id) return `/item/${esc.item_id}`;
  return null;
}

/**
 * Get target entity admin link path for an escalation request (custodian view).
 * Links manifestations to the FRBR Metadata Editor so custodians can edit the entity.
 *
 * @param esc - Escalation request object.
 * @returns Admin target URL path or null if no target entity is set.
 */
export function getAdminTargetHref(esc: EscalationRequest): string | null {
  if (esc.manifestation_id) return `/admin/content?tab=metadata&manifestationId=${esc.manifestation_id}`;
  // See getTargetHref: an Expression escalation has work_id NULL, so the old
  // `&& esc.work_id` guard sent every one of them to `null` here too.
  if (esc.expression_id) return `/expression/${esc.expression_id}`;
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
  if (esc.target_type) {
    const levelName = esc.target_type.charAt(0).toUpperCase() + esc.target_type.slice(1);
    return `${levelName} (deleted)`;
  }
  return "FRBR Entity (deleted)";
}
