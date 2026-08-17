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
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { useTranslations } from "next-intl";
import { useDistributionInsights } from "@/lib/api/hooks";
import { PieChart as PieIcon, AlertCircle } from "lucide-react";

const COLORS = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#14b8a6", // teal
  "#6366f1", // indigo
  "#f43f5e", // rose
];

/**
 * Renders a pie/donut chart representing collection distribution by type or format.
 *
 * @param {object} [props] - Component props
 * @param {"personal" | "global"} [props.scope="personal"] - Data scope
 * @returns {JSX.Element} Component JSX
 */
export function TypeDistributionChart({ scope = "personal" }: { scope?: "personal" | "global" } = {}) {
  const t = useTranslations("CollectionInsights");
  const { data: distributionData, isLoading, isError } = useDistributionInsights(scope);
  const [activeTab, setActiveTab] = React.useState<"type" | "format">("type");

  if (isLoading) {
    return (
      <div data-testid="distribution-chart-skeleton" className="flex h-72 flex-col justify-between p-4 animate-pulse">
        <div className="h-4 w-1/3 rounded bg-muted" />
        <div className="mx-auto h-40 w-40 rounded-full bg-muted" />
      </div>
    );
  }

  if (isError || !distributionData) {
    return (
      <div
        data-testid="distribution-chart-error"
        className="flex h-72 flex-col items-center justify-center gap-2 text-muted-foreground"
      >
        <AlertCircle className="h-6 w-6 text-destructive" />
        <p className="text-sm font-medium">{t("emptyState")}</p>
      </div>
    );
  }

  const rawData = activeTab === "type" ? distributionData.by_type : distributionData.by_format;
  const chartData = rawData.map(item => ({
    name: "type" in item ? item.type : item.format,
    value: item.count,
  }));

  const totalCount = chartData.reduce((acc, curr) => acc + curr.value, 0);

  return (
    <div
      data-testid="type-distribution-chart"
      className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5 shadow-sm"
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-base font-semibold text-foreground">
            <PieIcon className="h-4 w-4 text-primary" />
            {t("distributionTitle")}
          </h3>
          <p className="text-xs text-muted-foreground">{t("distributionDesc")}</p>
        </div>

        {/* Tab switcher */}
        <div className="inline-flex rounded-lg bg-muted p-1">
          <button
            onClick={() => setActiveTab("type")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activeTab === "type" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t("byType")}
          </button>
          <button
            onClick={() => setActiveTab("format")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activeTab === "format"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t("byFormat")}
          </button>
        </div>
      </div>

      {chartData.length === 0 || totalCount === 0 ? (
        <div className="flex h-56 flex-col items-center justify-center text-muted-foreground">
          <p className="text-xs italic">{t("emptyState")}</p>
        </div>
      ) : (
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--background)",
                  borderColor: "var(--border)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                formatter={(value: unknown) => [`${value ?? 0} items`, "Count"]}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                formatter={(value: string) => <span className="text-xs text-foreground capitalize">{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
