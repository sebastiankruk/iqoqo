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

import { BarChart3, BookCheck, Clock, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useManifestationStats } from "@/lib/api/hooks/catalog";

export interface ManifestationStatsCardProps {
  manifestationId: number;
}

/**
 * Displays anonymized reading statistics and monthly popularity over time for a Manifestation (F3).
 */
export function ManifestationStatsCard({ manifestationId }: ManifestationStatsCardProps) {
  const t = useTranslations("Manifestation");
  const { data: stats, isLoading } = useManifestationStats(manifestationId);

  if (isLoading || !stats) {
    return null;
  }

  const maxCount = Math.max(1, ...stats.popularity_over_time.map(b => Math.max(b.added_count, b.completed_count)));
  const hasActivity = stats.total_items > 0 || stats.popularity_over_time.length > 0;

  return (
    <div
      className="mt-8 rounded-xl border border-border bg-card p-5 shadow-sm space-y-4"
      data-testid="manifestation-stats-card"
    >
      <div className="flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-primary" />
        <h3 className="font-serif text-lg font-bold text-foreground">{t("readStatsTitle")}</h3>
      </div>

      {!hasActivity ? (
        <p className="text-sm text-muted-foreground italic">{t("readStatsEmpty")}</p>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg border border-border bg-background/60 p-3">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Users className="h-3.5 w-3.5" />
                <span>{t("statReaders")}</span>
              </div>
              <p className="mt-1 text-xl font-bold tabular-nums">{stats.reader_count}</p>
            </div>
            <div className="rounded-lg border border-border bg-background/60 p-3">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <BookCheck className="h-3.5 w-3.5" />
                <span>{t("statCompleted")}</span>
              </div>
              <p className="mt-1 text-xl font-bold tabular-nums">{stats.completed_count}</p>
            </div>
            <div className="rounded-lg border border-border bg-background/60 p-3">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>{t("statAvgMinutes")}</span>
              </div>
              <p className="mt-1 text-xl font-bold tabular-nums">
                {stats.avg_session_minutes !== null ? `${stats.avg_session_minutes}m` : "—"}
              </p>
            </div>
            <div className="rounded-lg border border-border bg-background/60 p-3">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>{t("statAvgDays")}</span>
              </div>
              <p className="mt-1 text-xl font-bold tabular-nums">
                {stats.avg_reading_days !== null ? `${stats.avg_reading_days}d` : "—"}
              </p>
            </div>
          </div>

          {stats.popularity_over_time.length > 0 && (
            <div className="space-y-2 pt-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("popularityOverTime")}
              </p>
              <div className="flex items-end gap-2 h-24 pt-2" data-testid="popularity-chart">
                {stats.popularity_over_time.map(bucket => {
                  const addedPct = Math.round((bucket.added_count / maxCount) * 100);
                  const completedPct = Math.round((bucket.completed_count / maxCount) * 100);
                  return (
                    <div
                      key={bucket.month}
                      className="flex-1 flex flex-col items-center gap-1 h-full justify-end min-w-0"
                    >
                      <div className="w-full flex items-end justify-center gap-0.5 h-16">
                        <div
                          title={`${bucket.month}: +${bucket.added_count}`}
                          style={{ height: `${Math.max(addedPct, bucket.added_count > 0 ? 12 : 0)}%` }}
                          className="w-2.5 rounded-t bg-primary/80 transition-all"
                        />
                        <div
                          title={`${bucket.month}: ✓${bucket.completed_count}`}
                          style={{ height: `${Math.max(completedPct, bucket.completed_count > 0 ? 12 : 0)}%` }}
                          className="w-2.5 rounded-t bg-emerald-500/80 transition-all"
                        />
                      </div>
                      <span className="text-[10px] text-muted-foreground truncate w-full text-center">
                        {bucket.month.slice(2)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
