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

import { apiFetch } from "@/lib/api/client";
import type { VelocityPoint, InsightsData } from "@/types/insights";

/**
 * Fetch monthly item acquisition velocity for the authenticated user.
 *
 * @returns {Promise<VelocityPoint[]>} Array of monthly counts
 */
export async function getVelocityInsights(): Promise<VelocityPoint[]> {
  return apiFetch<VelocityPoint[]>("/profile/insights/velocity");
}

/**
 * Fetch collection distribution by content_type and format for the authenticated user.
 *
 * @returns {Promise<InsightsData>} Distribution data
 */
export async function getDistributionInsights(): Promise<InsightsData> {
  return apiFetch<InsightsData>("/profile/insights/distribution");
}
