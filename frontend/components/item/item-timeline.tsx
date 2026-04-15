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

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Clock, History } from "lucide-react";

interface StatusLog {
  old_status: string | null;
  new_status: string;
  changed_at: string;
}

/**
 * Item provenance timeline component.
 *
 * @param {object} props - Component props.
 * @param {number} props.itemId - The ID of the item.
 * @returns {JSX.Element | null} The component or null if no logs.
 */
export function ItemProvenanceTimeline({ itemId }: { itemId: number }) {
  const { data: logs, isLoading, error } = useQuery<StatusLog[]>({
    queryKey: ["item", itemId, "logs"],
    queryFn: async () => {
      const res = await apiClient.get(`/items/${itemId}/logs`);
      if (!res.data?.success) throw new Error(res.data?.error ?? "Failed to load history");
      return res.data.data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center text-destructive text-xs">
        Failed to load item history.
      </div>
    );
  }

  if (!logs || logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <History className="h-6 w-6 text-muted-foreground" />
        </div>
        <h3 className="mt-4 text-sm font-semibold text-foreground">No history yet</h3>
        <p className="mt-1 text-xs text-muted-foreground">Status changes will appear here.</p>
      </div>
    );
  }

  return (
    <div className="relative space-y-6 before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:bg-gradient-to-b before:from-border before:to-transparent sm:before:ml-[2.25rem]">
      {logs.map((log, i) => (
        <div key={i} className="relative flex items-start gap-4 sm:gap-6">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary ring-4 ring-background sm:h-12 sm:w-12">
            <Clock className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="flex flex-col pt-1 sm:pt-2">
            <div className="text-sm font-medium text-foreground">
              Status changed to{" "}
              <span className="font-bold text-primary capitalize">{log.new_status.replace(/_/g, " ")}</span>
            </div>
            {log.old_status && (
              <div className="text-xs text-muted-foreground mt-0.5">
                Previously: <span className="capitalize">{log.old_status.replace(/_/g, " ")}</span>
              </div>
            )}
            <time className="mt-1 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
              {new Intl.DateTimeFormat("en-US", {
                dateStyle: "full",
                timeStyle: "short",
              }).format(new Date(log.changed_at))}
            </time>
          </div>
        </div>
      ))}
    </div>
  );
}
