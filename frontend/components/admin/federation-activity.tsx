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
"use client";

import { useState, useEffect } from "react";
import { getFederationActivities } from "@/lib/api/federation";
import { Loader2, ArrowDownLeft, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { FederationActivity, FederationActivityFilters, PaginationMeta } from "@/types/federation";

/**
 * Displays paginated federation activity log with filtering.
 * @returns {JSX.Element} The component
 */
export function FederationActivityLog() {
  const [activities, setActivities] = useState<FederationActivity[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FederationActivityFilters>({});

  useEffect(() => {
    const fetchActivities = async () => {
      setLoading(true);
      try {
        const result = await getFederationActivities(page, filters);
        setActivities(result.data);
        setPagination(result.pagination);
      } catch (e) {
        console.error("Failed to fetch activities", e);
      } finally {
        setLoading(false);
      }
    };
    fetchActivities();
  }, [page, filters]);

  const STATUS_COLORS: Record<string, string> = {
    queued: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    delivered: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm"
          value={filters.direction || ""}
          onChange={e => setFilters({ ...filters, direction: (e.target.value as "inbound" | "outbound") || undefined })}
        >
          <option value="">All Directions</option>
          <option value="inbound">Inbound</option>
          <option value="outbound">Outbound</option>
        </select>
        <select
          className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm"
          value={filters.status || ""}
          onChange={e =>
            setFilters({ ...filters, status: (e.target.value as "queued" | "delivered" | "failed") || undefined })
          }
        >
          <option value="">All Statuses</option>
          <option value="queued">Queued</option>
          <option value="delivered">Delivered</option>
          <option value="failed">Failed</option>
        </select>
        <input
          type="text"
          className="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm"
          value={filters.type || ""}
          onChange={e => setFilters({ ...filters, type: e.target.value || undefined })}
          placeholder="Activity type..."
        />
      </div>

      {loading ? (
        <Loader2 className="animate-spin h-6 w-6 text-muted-foreground my-10 mx-auto" />
      ) : activities.length === 0 ? (
        <p className="text-sm text-muted-foreground">No federation activities found.</p>
      ) : (
        <>
          <div className="border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Direction</th>
                  <th className="text-left px-4 py-2 font-medium">Type</th>
                  <th className="text-left px-4 py-2 font-medium">Actor</th>
                  <th className="text-left px-4 py-2 font-medium">Status</th>
                  <th className="text-left px-4 py-2 font-medium">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {activities.map(activity => (
                  <tr key={activity.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3">
                      {activity.direction === "inbound" ? (
                        <ArrowDownLeft className="h-4 w-4 text-blue-500" />
                      ) : (
                        <ArrowUpRight className="h-4 w-4 text-green-500" />
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">{activity.activity_type}</td>
                    <td className="px-4 py-3 text-muted-foreground truncate max-w-[200px]">{activity.actor_uri}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded ${STATUS_COLORS[activity.status] || ""}`}>
                        {activity.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {activity.created_at ? new Date(activity.created_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pagination && pagination.pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Page {pagination.page} of {pagination.pages} ({pagination.total} total)
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= pagination.pages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
