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
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { useTranslations } from "next-intl";
import { useVelocityInsights } from "@/lib/api/hooks";
import { TrendingUp, AlertCircle } from "lucide-react";

/**
 * Renders a bar chart representing monthly item acquisition velocity.
 *
 * @param {object} [props] - Component props
 * @param {"personal" | "global"} [props.scope="personal"] - Data scope
 * @returns {JSX.Element} Component JSX
 */
export function VelocityChart({ scope = "personal" }: { scope?: "personal" | "global" } = {}) {
  const t = useTranslations("CollectionInsights");
  const { data: velocityData, isLoading, isError } = useVelocityInsights(scope);

  if (isLoading) {
    return (
      <div data-testid="velocity-chart-skeleton" className="flex h-72 flex-col justify-between p-4 animate-pulse">
        <div className="h-4 w-1/3 rounded bg-muted" />
        <div className="flex h-48 items-end gap-2">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="flex-1 rounded-t bg-muted" style={{ height: `${((i % 5) + 2) * 18}%` }} />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !velocityData) {
    return (
      <div
        data-testid="velocity-chart-error"
        className="flex h-72 flex-col items-center justify-center gap-2 text-muted-foreground"
      >
        <AlertCircle className="h-6 w-6 text-destructive" />
        <p className="text-sm font-medium">{t("emptyState")}</p>
      </div>
    );
  }

  // Format month label for axis e.g. "2026-07" -> "07/26"
  const formattedData = velocityData.map(item => {
    const parts = item.month.split("-");
    const label = parts.length === 2 ? `${parts[1]}/${parts[0].slice(2)}` : item.month;
    return { ...item, displayMonth: label };
  });

  return (
    <div
      data-testid="velocity-chart"
      className="flex flex-col gap-4 rounded-xl border border-border bg-card p-5 shadow-sm"
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-base font-semibold text-foreground">
            <TrendingUp className="h-4 w-4 text-primary" />
            {t("velocityTitle")}
          </h3>
          <p className="text-xs text-muted-foreground">{t("velocityDesc")}</p>
        </div>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={formattedData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis dataKey="displayMonth" tick={{ fontSize: 11 }} stroke="#888888" tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 11 }} stroke="#888888" allowDecimals={false} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: "var(--background)",
                borderColor: "var(--border)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              formatter={(value: unknown) => [`${value ?? 0} items`, "Added"]}
              labelFormatter={(label: React.ReactNode) => `Month: ${String(label ?? "")}`}
            />
            <Bar dataKey="count" fill="var(--primary, #3b82f6)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
