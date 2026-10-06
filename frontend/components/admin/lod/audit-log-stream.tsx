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

import { useState, useRef, useEffect, useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  CheckCircle2,
  AlertTriangle,
  MinusCircle,
  Globe,
  MapPin,
  BookMarked,
  ArrowDownToLine,
  Filter,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { LODLogEntry } from "@/types/admin";

export interface AuditLogStreamProps {
  logs?: LODLogEntry[];
  isLoading?: boolean;
  className?: string;
}

type FilterOutcome = "all" | "success" | "skipped" | "warn";

/**
 * Live resolution audit log stream component.
 *
 * Displays chronological item-by-item resolution outcomes with authority badges,
 * outcome filtering, and auto-scroll capability.
 *
 * @param props - Component properties containing log entries and loading state.
 * @returns React component with scrollable resolution log entries.
 */
export function AuditLogStream({ logs = [], isLoading = false, className }: AuditLogStreamProps) {
  const t = useTranslations("LodReconciliation.auditLog");
  const [filter, setFilter] = useState<FilterOutcome>("all");
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  const filteredLogs = useMemo(() => {
    if (!logs) return [];
    return logs.filter(entry => {
      const status = entry.status?.toUpperCase();
      if (filter === "success") return status === "SUCCESS";
      if (filter === "skipped") return status === "SKIPPED";
      if (filter === "warn") return status === "WARN" || status === "FAILED";
      return true;
    });
  }, [logs, filter]);

  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return iso;
    }
  };

  return (
    <Card data-testid="lod-audit-log-card" className={`border-border/60 shadow-sm ${className ?? ""}`}>
      <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3">
        <div>
          <CardTitle className="text-lg font-semibold">{t("title")}</CardTitle>
          <CardDescription className="text-sm text-muted-foreground mt-0.5">{t("description")}</CardDescription>
        </div>

        {/* Filter controls: uses a single Select dropdown and 1 toggle button to conserve button budget */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Filter className="h-3.5 w-3.5 text-muted-foreground" />
            <Select value={filter} onValueChange={v => setFilter(v as FilterOutcome)}>
              <SelectTrigger
                data-testid="lod-log-filter-select"
                aria-label={t("filterAll")}
                className="h-8 w-[140px] text-xs"
              >
                <SelectValue placeholder={t("filterAll")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t("filterAll")}</SelectItem>
                <SelectItem value="success">{t("filterSuccess")}</SelectItem>
                <SelectItem value="skipped">{t("filterSkipped")}</SelectItem>
                <SelectItem value="warn">{t("filterWarn")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button
            data-testid="lod-autoscroll-toggle"
            variant={autoScroll ? "default" : "outline"}
            size="sm"
            onClick={() => setAutoScroll(prev => !prev)}
            className={cn(
              "h-8 px-2.5 text-xs gap-1.5 font-medium transition-all",
              autoScroll
                ? "bg-primary text-primary-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            )}
            title={t("autoScroll")}
          >
            <ArrowDownToLine className="h-3.5 w-3.5" />
            <span>{autoScroll ? "Auto-scroll: ON" : "Auto-scroll: OFF"}</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        <div
          ref={scrollContainerRef}
          data-testid="lod-log-scroll-container"
          className="h-[360px] overflow-y-auto rounded-md border border-border/40 bg-muted/20 p-3 flex flex-col gap-2 font-mono text-xs"
        >
          {filteredLogs.length === 0 ? (
            <div
              data-testid="lod-no-logs-message"
              className="h-full flex flex-col items-center justify-center text-center p-6 text-muted-foreground font-sans gap-1"
            >
              {/* A scan that has not produced its first event yet is not the
                  same as a scan that has produced none at all. The parent
                  passes `isProcessing` for exactly this distinction, and the
                  previous version dropped it -- so a running reconciliation
                  announced "no resolution events yet" while it was working,
                  which reads as a completed run that found nothing. */}
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  <p className="text-sm" data-testid="lod-log-loading-message">
                    {t("loadingLog")}
                  </p>
                </>
              ) : (
                <p className="text-sm">{t("noLogs")}</p>
              )}
            </div>
          ) : (
            filteredLogs.map((entry, index) => {
              const statusUpper = entry.status?.toUpperCase();
              const isSuccess = statusUpper === "SUCCESS";
              const isSkipped = statusUpper === "SKIPPED";
              const isWarn = statusUpper === "WARN" || statusUpper === "FAILED";

              return (
                <div
                  key={`${entry.manifestation_id}-${entry.timestamp}-${index}`}
                  data-testid="lod-log-entry"
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 rounded-md bg-background/80 border border-border/40 hover:bg-background transition-colors"
                >
                  <div className="flex items-start sm:items-center gap-2 min-w-0">
                    <span className="text-muted-foreground shrink-0 select-none">
                      [{formatTimestamp(entry.timestamp)}]
                    </span>

                    {/* Outcome Badge */}
                    {isSuccess && (
                      <Badge
                        variant="default"
                        className="bg-emerald-600/15 text-emerald-700 dark:text-emerald-400 border-emerald-300 dark:border-emerald-800 shrink-0 gap-1 px-1.5 py-0 text-[10px]"
                      >
                        <CheckCircle2 className="h-3 w-3" />
                        <span>SUCCESS</span>
                      </Badge>
                    )}
                    {isSkipped && (
                      <Badge
                        variant="secondary"
                        className="shrink-0 gap-1 px-1.5 py-0 text-[10px] text-muted-foreground"
                      >
                        <MinusCircle className="h-3 w-3" />
                        <span>SKIPPED</span>
                      </Badge>
                    )}
                    {isWarn && (
                      <Badge variant="destructive" className="shrink-0 gap-1 px-1.5 py-0 text-[10px]">
                        <AlertTriangle className="h-3 w-3" />
                        <span>{statusUpper}</span>
                      </Badge>
                    )}

                    {/* Manifestation identifier & title */}
                    <span className="truncate font-sans text-xs text-foreground font-medium">
                      #{entry.manifestation_id} · {entry.title}
                    </span>
                  </div>

                  {/* Right side: Authority links & counts */}
                  <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center font-sans">
                    {entry.authorities?.includes("dbpedia") && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-500/10 text-blue-600 dark:text-blue-400">
                        <Globe className="h-2.5 w-2.5" />
                        DBpedia
                      </span>
                    )}
                    {entry.authorities?.includes("geonames") && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                        <MapPin className="h-2.5 w-2.5" />
                        GeoNames
                      </span>
                    )}
                    {entry.authorities?.includes("wordnet") && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-500/10 text-purple-600 dark:text-purple-400">
                        <BookMarked className="h-2.5 w-2.5" />
                        WordNet
                      </span>
                    )}

                    <span className="text-[11px] text-muted-foreground ml-1">
                      {entry.links_added > 0 ? t("linksAdded", { count: entry.links_added }) : t("noLinksAdded")}
                    </span>

                    {entry.error && (
                      <span className="text-[11px] text-destructive truncate max-w-[150px]" title={entry.error}>
                        ({entry.error})
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}
