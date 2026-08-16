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

import * as React from "react";
import { useTranslations } from "next-intl";
import { useStats } from "@/lib/api/hooks";
import { VelocityChart } from "./velocity-chart";
import { TypeDistributionChart } from "./type-distribution-chart";
import { BarChart3 } from "lucide-react";

/**
 * Renders the collector insights section with velocity and distribution charts.
 *
 * @param {object} [props] - Component props
 * @param {boolean} [props.showTitle=true] - Whether to render section heading
 * @param {"personal" | "global"} [props.scope="personal"] - Data scope
 * @returns {JSX.Element | null} Component JSX
 */
export function CollectionInsights({
  showTitle = true,
  scope = "personal",
}: {
  showTitle?: boolean;
  scope?: "personal" | "global";
} = {}) {
  const t = useTranslations("CollectionInsights");
  const { data: stats } = useStats(scope);

  if (stats && stats.total_items === 0) {
    return null;
  }

  return (
    <section data-testid="collection-insights" className={showTitle ? "mt-8 space-y-4" : "space-y-4"}>
      {showTitle && (
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-bold tracking-tight text-foreground">{t("title")}</h2>
        </div>
      )}

      <div className="flex gap-6 overflow-x-auto flex-nowrap pb-2 sm:grid sm:grid-cols-1 lg:grid-cols-2 sm:pb-0 sm:overflow-visible">
        <div className="min-w-[85vw] max-w-[90vw] sm:min-w-0 sm:max-w-none shrink-0 sm:shrink">
          <VelocityChart scope={scope} />
        </div>
        <div className="min-w-[85vw] max-w-[90vw] sm:min-w-0 sm:max-w-none shrink-0 sm:shrink">
          <TypeDistributionChart scope={scope} />
        </div>
      </div>
    </section>
  );
}
