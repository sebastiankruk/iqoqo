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

import { useTranslations } from "next-intl";
import { Globe, MapPin, BookMarked, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LODStats, LODAuthorityCounts } from "@/types/admin";

export interface MetricCardsProps {
  stats?: LODStats;
  taskCounts?: LODAuthorityCounts;
  totalProcessed?: number;
  isProcessing?: boolean;
}

/**
 * Metric summary cards displaying catalog-wide and active-task LOD authority statistics.
 *
 * @param props - Component properties containing LODStats and active task counts.
 * @returns React component with 4 responsive summary cards.
 */
export function MetricCards({ stats, taskCounts, totalProcessed, isProcessing = false }: MetricCardsProps) {
  const t = useTranslations("LodReconciliation.metrics");

  const totalManifestations = stats?.total_manifestations ?? 0;
  const linkedManifestations = stats?.linked_manifestations ?? 0;
  const unlinkedManifestations = stats?.unlinked_manifestations ?? 0;

  const dbpediaCount = stats?.by_authority?.dbpedia ?? 0;
  const geonamesCount = stats?.by_authority?.geonames ?? 0;
  const wordnetCount = stats?.by_authority?.wordnet ?? 0;

  const activeDbpedia = taskCounts?.dbpedia ?? 0;
  const activeGeonames = taskCounts?.geonames ?? 0;
  const activeWordnet = taskCounts?.wordnet ?? 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Total Editions */}
      <Card data-testid="metric-card-manifestations" className="border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-sm font-medium text-muted-foreground">{t("totalManifestations")}</CardTitle>
          <Layers className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight">{totalManifestations.toLocaleString()}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {isProcessing && totalProcessed !== undefined ? (
              <span className="text-primary font-medium">{totalProcessed.toLocaleString()} processed in scan</span>
            ) : (
              <span>
                {linkedManifestations.toLocaleString()} linked · {unlinkedManifestations.toLocaleString()} unlinked
              </span>
            )}
          </p>
        </CardContent>
      </Card>

      {/* DBpedia */}
      <Card data-testid="metric-card-dbpedia" className="border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-sm font-medium text-muted-foreground">{t("dbpediaLinks")}</CardTitle>
          <Globe className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight text-blue-600 dark:text-blue-400">
            {dbpediaCount.toLocaleString()}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {activeDbpedia > 0 ? (
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                +{activeDbpedia.toLocaleString()} in active scan
              </span>
            ) : (
              "General knowledge & entities"
            )}
          </p>
        </CardContent>
      </Card>

      {/* GeoNames */}
      <Card data-testid="metric-card-geonames" className="border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-sm font-medium text-muted-foreground">{t("geonamesLinks")}</CardTitle>
          <MapPin className="h-4 w-4 text-emerald-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight text-emerald-600 dark:text-emerald-400">
            {geonamesCount.toLocaleString()}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {activeGeonames > 0 ? (
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                +{activeGeonames.toLocaleString()} in active scan
              </span>
            ) : (
              "Geographical places & locations"
            )}
          </p>
        </CardContent>
      </Card>

      {/* WordNet */}
      <Card data-testid="metric-card-wordnet" className="border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
          <CardTitle className="text-sm font-medium text-muted-foreground">{t("wordnetLinks")}</CardTitle>
          <BookMarked className="h-4 w-4 text-purple-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold tracking-tight text-purple-600 dark:text-purple-400">
            {wordnetCount.toLocaleString()}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {activeWordnet > 0 ? (
              <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                +{activeWordnet.toLocaleString()} in active scan
              </span>
            ) : (
              "Lexical synsets & categories"
            )}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
