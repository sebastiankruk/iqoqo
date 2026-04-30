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

import { BookMarked, BookOpen, HandHelping, Target } from "lucide-react";
import { useStats } from "@/lib/api/hooks";
import Link from "next/link";

/**
 * Three top-row stat cards pulled from the Flask /api/stats endpoint.
 *
 * @returns {JSX.Element} The component
 */
export function StatsCards() {
  const { data: stats, isLoading, isError } = useStats();

  const cards = [
    {
      label: "Items",
      value: stats?.total_items ?? 0,
      icon: BookOpen,
      borderColor: "border-l-primary",
      iconBg: "bg-primary/8",
      iconColor: "text-primary",
      description: "Total in collection",
      href: "/collection",
    },
    {
      label: "Reading",
      value: stats?.items_reading ?? 0,
      icon: BookMarked,
      borderColor: "border-l-green-500",
      iconBg: "bg-green-500/10",
      iconColor: "text-green-600",
      description: "Currently active reads",
      href: "/collection?statuses=reading",
    },
    {
      label: "On Wish List",
      value: stats?.to_read ?? 0,
      icon: Target,
      borderColor: "border-l-chart-3",
      iconBg: "bg-chart-3/10",
      iconColor: "text-chart-3",
      description: "On your list",
      href: "/collection?statuses=wish_list",
    },
    {
      label: "Lent Out",
      value: stats?.lent_items ?? 0,
      icon: HandHelping,
      borderColor: "border-l-accent",
      iconBg: "bg-accent/10",
      iconColor: "text-accent",
      description: "Currently with friends",
      href: "/collection?statuses=lent",
    },
    {
      label: "Borrowed",
      value: stats?.borrowed_items ?? 0,
      icon: BookMarked,
      borderColor: "border-l-teal-500",
      iconBg: "bg-teal-500/10",
      iconColor: "text-teal-600",
      description: "Borrowed from others",
      href: "/collection?borrowed=true",
    },
  ];

  return (
    <section aria-label="Collection statistics">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map(stat => (
          <Link
            key={stat.label}
            href={stat.href}
            className={`group relative overflow-hidden rounded-xl border-l-4 ${stat.borderColor} bg-card p-5 shadow-sm transition-shadow hover:shadow-md block`}
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
    </section>
  );
}
