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
 * @returns Component JSX
 */
export function CollectionInsights() {
  const t = useTranslations("CollectionInsights");
  const { data: stats } = useStats();

  if (stats && stats.total_items === 0) {
    return null;
  }

  return (
    <section data-testid="collection-insights" className="mt-8 space-y-4">
      <div className="flex items-center gap-2">
        <BarChart3 className="h-5 w-5 text-primary" />
        <h2 className="text-lg font-bold tracking-tight text-foreground">{t("title")}</h2>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <VelocityChart />
        <TypeDistributionChart />
      </div>
    </section>
  );
}
