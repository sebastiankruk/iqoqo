"use client";

import { BookOpen, HandHelping, Target } from "lucide-react";
import { useStats } from "@/lib/api/hooks";

/** Three top-row stat cards pulled from the Flask /api/stats endpoint. */
export function StatsCards() {
  const { data: stats, isLoading } = useStats();

  const cards = [
    {
      label: "Items",
      value: stats?.total_items ?? 0,
      icon: BookOpen,
      borderColor: "border-l-primary",
      iconBg: "bg-primary/8",
      iconColor: "text-primary",
      description: "Total in collection",
    },
    {
      label: "Lent Out",
      value: stats?.lent_items ?? 0,
      icon: HandHelping,
      borderColor: "border-l-accent",
      iconBg: "bg-accent/10",
      iconColor: "text-accent",
      description: "Currently with friends",
    },
    {
      label: "To Read",
      value: stats?.to_read ?? 0,
      icon: Target,
      borderColor: "border-l-chart-3",
      iconBg: "bg-chart-3/10",
      iconColor: "text-chart-3",
      description: "On your list",
    },
  ];

  return (
    <section aria-label="Collection statistics">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        {cards.map((stat) => (
          <div
            key={stat.label}
            className={`group relative overflow-hidden rounded-xl border-l-4 ${stat.borderColor} bg-card p-5 shadow-sm transition-shadow hover:shadow-md`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  {stat.label}
                </p>
                <p className="mt-1 font-serif text-3xl font-bold tracking-tight text-card-foreground">
                  {isLoading ? (
                    <span className="inline-block h-9 w-16 animate-pulse rounded bg-muted" />
                  ) : (
                    stat.value.toLocaleString()
                  )}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {stat.description}
                </p>
              </div>
              <div
                className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${stat.iconBg}`}
              >
                <stat.icon className={`h-5 w-5 ${stat.iconColor}`} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
