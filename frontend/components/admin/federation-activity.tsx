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

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Activity,
  ArrowDownLeft,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Filter,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useFederationActivities } from "@/lib/api/hooks/federation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { FederationActivityFilters } from "@/types/federation";

const ACTIVITY_TYPES = ["", "Follow", "Accept", "Reject", "Create", "Update", "Delete", "Undo", "Announce"];

/**
 * Render status badge component for activity status.
 *
 * @param status - Activity delivery status.
 * @param t - Translator function for AdminFederation namespace.
 * @returns Status badge element.
 */
function getStatusBadge(status: string, t: ReturnType<typeof useTranslations>) {
  switch (status) {
    case "delivered":
      return (
        <Badge variant="default" className="bg-green-600 text-white flex items-center gap-1">
          <CheckCircle2 className="h-3 w-3" /> {t("statusDelivered")}
        </Badge>
      );
    case "queued":
      return (
        <Badge variant="outline" className="text-yellow-600 border-yellow-500/40 flex items-center gap-1">
          <Clock className="h-3 w-3" /> {t("statusQueued")}
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="destructive" className="flex items-center gap-1">
          <XCircle className="h-3 w-3" /> {t("statusFailed")}
        </Badge>
      );
    default:
      return <Badge variant="secondary">{status}</Badge>;
  }
}

/**
 * Render direction badge component for inbound/outbound activities.
 *
 * @param direction - Direction string ('inbound' | 'outbound').
 * @param t - Translator function for AdminFederation namespace.
 * @returns Direction badge element.
 */
function getDirectionBadge(direction: string, t: ReturnType<typeof useTranslations>) {
  if (direction === "inbound") {
    return (
      <Badge variant="outline" className="text-blue-500 border-blue-500/30 flex items-center gap-1">
        <ArrowDownLeft className="h-3 w-3" /> {t("inbound")}
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="text-purple-500 border-purple-500/30 flex items-center gap-1">
      <ArrowUpRight className="h-3 w-3" /> {t("outbound")}
    </Badge>
  );
}

/**
 * FederationActivityLog component rendering searchable, filterable activity log.
 *
 * @returns Activity log component.
 */
export function FederationActivityLog() {
  const t = useTranslations("AdminFederation");
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FederationActivityFilters>({});

  const { data, isLoading, error, refetch, isFetching } = useFederationActivities(page, filters);

  const activities = data?.data || [];
  const pagination = data?.pagination || { page: 1, per_page: 20, total: 0, pages: 1 };

  const handleFilterChange = (key: keyof FederationActivityFilters, val: string) => {
    setFilters(prev => ({
      ...prev,
      [key]: val || undefined,
    }));
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                {t("activityLogTitle")}
              </CardTitle>
              <CardDescription>{t("activityLogDesc")}</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? "animate-spin" : ""}`} />
              {t("refresh")}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center gap-3 p-3 rounded-lg bg-muted/40 border border-border text-sm">
            <span className="flex items-center gap-1.5 font-medium text-muted-foreground text-xs uppercase tracking-wider">
              <Filter className="h-3.5 w-3.5" /> {t("filterLabel")}
            </span>

            {/* Direction */}
            <select
              value={filters.direction || ""}
              onChange={e => handleFilterChange("direction", e.target.value)}
              className="text-xs h-8 rounded border border-input bg-background px-2.5 shadow-sm"
            >
              <option value="">{t("allDirections")}</option>
              <option value="inbound">{t("inbound")}</option>
              <option value="outbound">{t("outbound")}</option>
            </select>

            {/* Type */}
            <select
              value={filters.type || ""}
              onChange={e => handleFilterChange("type", e.target.value)}
              className="text-xs h-8 rounded border border-input bg-background px-2.5 shadow-sm"
            >
              <option value="">{t("allTypes")}</option>
              {ACTIVITY_TYPES.filter(Boolean).map(typeKey => (
                <option key={typeKey} value={typeKey}>
                  {typeKey}
                </option>
              ))}
            </select>

            {/* Status */}
            <select
              value={filters.status || ""}
              onChange={e => handleFilterChange("status", e.target.value)}
              className="text-xs h-8 rounded border border-input bg-background px-2.5 shadow-sm"
            >
              <option value="">{t("allStatuses")}</option>
              <option value="queued">{t("statusQueued")}</option>
              <option value="delivered">{t("statusDelivered")}</option>
              <option value="failed">{t("statusFailed")}</option>
            </select>
          </div>

          {/* Activities Table */}
          {isLoading ? (
            <div className="p-12 flex items-center justify-center text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>{t("loadingActivities")}</span>
            </div>
          ) : error ? (
            <div className="p-4 rounded-md bg-destructive/10 text-destructive text-sm">
              {t("failedLoadActivities")}: {error instanceof Error ? error.message : "Unknown error"}
            </div>
          ) : activities.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground space-y-2">
              <Activity className="h-8 w-8 mx-auto opacity-40" />
              <p className="text-sm font-medium">{t("noActivities")}</p>
              <p className="text-xs">{t("noActivitiesDesc")}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-muted/40 border-b border-border">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t("thTimestamp")}</th>
                    <th className="px-4 py-3 font-medium">{t("thDirection")}</th>
                    <th className="px-4 py-3 font-medium">{t("thType")}</th>
                    <th className="px-4 py-3 font-medium">{t("thActorTarget")}</th>
                    <th className="px-4 py-3 font-medium">{t("thStatus")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {activities.map(act => (
                    <tr key={act.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                        {act.created_at ? new Date(act.created_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-4 py-3">{getDirectionBadge(act.direction, t)}</td>
                      <td className="px-4 py-3 font-mono text-xs font-semibold">{act.activity_type}</td>
                      <td className="px-4 py-3 text-xs max-w-xs truncate" title={act.target_uri || act.actor_uri}>
                        <span className="font-mono text-muted-foreground">{act.actor_uri}</span>
                        {act.target_uri && (
                          <span className="block text-[11px] text-muted-foreground/75 truncate">
                            → {act.target_uri}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">{getStatusBadge(act.status, t)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {pagination.pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-border text-xs text-muted-foreground">
              <span>{t("pageInfo", { page: pagination.page, pages: pagination.pages, total: pagination.total })}</span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  aria-label={t("prevPageAria")}
                >
                  {t("previous")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.min(pagination.pages, p + 1))}
                  disabled={page >= pagination.pages}
                  aria-label={t("nextPageAria")}
                >
                  {t("next")}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
