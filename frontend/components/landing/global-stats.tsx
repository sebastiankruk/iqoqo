"use client";

import { useGlobalStats } from "@/lib/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, Layers, Library, Users } from "lucide-react";

export function GlobalStats() {
  const { data: stats, isLoading } = useGlobalStats();

  if (isLoading || !stats) return null;

  const statItems = [
    { title: "Works", value: stats.works, icon: BookOpen },
    { title: "Manifestations", value: stats.manifestations, icon: Layers },
    { title: "Items Tracked", value: stats.items, icon: Library },
    { title: "Curators", value: stats.users, icon: Users },
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
