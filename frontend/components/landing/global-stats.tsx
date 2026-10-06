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

import { useGlobalStats } from "@/lib/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, Layers, Library, Users } from "lucide-react";
import { useTranslations } from "next-intl";

/**
 * Global stats section component.
 *
 * @returns {JSX.Element | null} The component
 */
export function GlobalStats() {
  const t = useTranslations("GlobalStats");
  const { data: stats, isLoading } = useGlobalStats();

  if (isLoading || !stats) {
    // Reserve the same box the real grid occupies. Returning null here made
    // the strip appear only after its fetch landed, pushing the sections below
    // it down -- Cumulative Layout Shift, on the landing page, above the fold.
    return (
      <div
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-12"
        data-testid="global-stats-skeleton"
        aria-hidden="true"
      >
        {[0, 1, 2, 3].map(i => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const statItems = [
    { title: t("works"), value: stats.works, icon: BookOpen },
    { title: t("manifestations"), value: stats.manifestations, icon: Layers },
    { title: t("itemsTracked"), value: stats.items, icon: Library },
    { title: t("curators"), value: stats.users, icon: Users },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-12">
      {statItems.map((stat, i) => {
        const Icon = stat.icon;
        return (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value.toLocaleString()}</div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
