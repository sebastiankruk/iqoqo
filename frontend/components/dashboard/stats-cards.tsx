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
import { BookMarked, BookOpen, Globe, HandHelping, Target, User, Users } from "lucide-react";
import { useStats } from "@/lib/api/hooks";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { CollectionInsights } from "./collection-insights";

/**
 * Top-row stat cards pulled from the Flask /api/stats endpoint with view (Stats / Insights) and scope (Personal / Friends / Global) toggles.
 *
 * @returns {JSX.Element} The component
 */
export function StatsCards() {
  const t = useTranslations("StatsCards");
  const [viewMode, setViewMode] = useState<"stats" | "insights">("stats");
  const [scope, setScope] = useState<"personal" | "friends" | "global">("personal");
  const { data: stats, isLoading, isError } = useStats(scope);

  const topCards = [
    {
      label:
        scope === "global" ? t("itemsGlobal") : scope === "friends" ? t("scopeFriends") || "Friends Items" : t("items"),
      value: stats?.total_items ?? 0,
      icon: BookOpen,
      borderColor: "border-l-primary",
      iconBg: "bg-primary/8",
      iconColor: "text-primary",
      description:
        scope === "global"
          ? t("itemsDescGlobal")
          : scope === "friends"
            ? t("itemsDescFriends") || "Total in friends' collections"
            : t("itemsDesc"),
      href: scope === "friends" ? "/collection?scope=friends" : "/collection",
    },
    {
      label: scope === "global" ? t("readingGlobal") : t("reading"),
      value: stats?.items_reading ?? 0,
      icon: BookMarked,
      borderColor: "border-l-green-500",
      iconBg: "bg-green-500/10",
      iconColor: "text-green-600",
      description: scope === "global" ? t("readingDescGlobal") : t("readingDesc"),
      href: scope === "friends" ? "/collection?scope=friends&statuses=reading" : "/collection?statuses=reading",
    },
    {
      label: scope === "global" ? t("wishListGlobal") : t("wishList"),
      value: stats?.to_read ?? 0,
      icon: Target,
      borderColor: "border-l-chart-3",
      iconBg: "bg-chart-3/10",
      iconColor: "text-chart-3",
      description: scope === "global" ? t("wishListDescGlobal") : t("wishListDesc"),
      href: scope === "friends" ? "/collection?scope=friends&statuses=wish_list" : "/collection?statuses=wish_list",
    },
    {
      label: t("lentOut"),
      value: stats?.lent_items ?? 0,
      icon: HandHelping,
      borderColor: "border-l-accent",
      iconBg: "bg-accent/10",
      iconColor: "text-accent",
      description: t("lentOutDesc"),
      href: "/collection?statuses=lent",
    },
    {
      label: t("borrowed"),
      value: stats?.borrowed_items ?? 0,
      icon: BookMarked,
      borderColor: "border-l-teal-500",
      iconBg: "bg-teal-500/10",
      iconColor: "text-teal-600",
      description: t("borrowedDesc"),
      href: "/collection?statuses=borrowed",
    },
  ];

  return (
    <section aria-label={t("ariaLabel")} className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          className="flex items-center gap-1 rounded-lg bg-muted/60 p-1 text-xs font-medium"
          role="group"
          aria-label={t("viewLabel")}
        >
          <button
            type="button"
            onClick={() => setViewMode("stats")}
            aria-pressed={viewMode === "stats"}
            className={`rounded-md px-3 py-1.5 transition-all ${
              viewMode === "stats"
                ? "bg-card text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t("viewStats")}
          </button>
          <button
            type="button"
            onClick={() => setViewMode("insights")}
            aria-pressed={viewMode === "insights"}
            className={`rounded-md px-3 py-1.5 transition-all ${
              viewMode === "insights"
                ? "bg-card text-foreground shadow-xs font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t("viewInsights")}
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label={
              scope === "personal" ? t("scopePersonal") : scope === "friends" ? t("scopeFriends") : t("scopeGlobal")
            }
            title={
              scope === "personal" ? t("scopePersonal") : scope === "friends" ? t("scopeFriends") : t("scopeGlobal")
            }
            onClick={() => {
              setScope(prev => (prev === "personal" ? "friends" : prev === "friends" ? "global" : "personal"));
            }}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-border/80 text-muted-foreground hover:text-foreground transition-colors"
          >
            {scope === "personal" ? (
              <User className="h-4 w-4" />
            ) : scope === "friends" ? (
              <Users className="h-4 w-4" />
            ) : (
              <Globe className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {viewMode === "stats" ? (
        <div
          data-testid="stats-scroll-container"
          className="flex gap-5 overflow-x-auto flex-nowrap pb-2 sm:grid sm:grid-cols-2 lg:grid-cols-5 sm:pb-0 sm:overflow-visible"
        >
          {topCards.map(stat => (
            <Link
              key={stat.label}
              href={stat.href}
              className={`group relative min-w-[220px] shrink-0 sm:min-w-0 sm:shrink overflow-hidden rounded-xl border-l-4 ${stat.borderColor} bg-card p-5 shadow-sm transition-shadow hover:shadow-md block`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{stat.label}</p>
                  <p className="mt-1 font-serif text-3xl font-bold tracking-tight text-card-foreground">
                    {isLoading ? (
                      <span className="inline-block h-9 w-16 animate-pulse rounded bg-muted" />
                    ) : isError ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      stat.value.toLocaleString()
                    )}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">{stat.description}</p>
                </div>
                <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${stat.iconBg}`}>
                  <stat.icon className={`h-5 w-5 ${stat.iconColor}`} />
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <CollectionInsights showTitle={false} scope={scope} />
      )}
    </section>
  );
}
