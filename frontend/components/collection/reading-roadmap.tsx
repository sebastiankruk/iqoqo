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

import React, { useState } from "react";
import { Milestone, BookOpen, CheckCircle2, Calendar, MoveUp, MoveDown, FileText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface RoadmapItem {
  id: number;
  title: string;
  creator: string;
  status: "queued" | "in_progress" | "completed";
  target_date?: string;
  notes?: string;
}

interface ReadingRoadmapProps {
  initialItems: RoadmapItem[];
  roadmapTitle: string;
  description?: string;
}

export const ReadingRoadmapComponent: React.FC<ReadingRoadmapProps> = ({ initialItems, roadmapTitle, description }) => {
  const [items, setItems] = useState<RoadmapItem[]>(initialItems);

  const shiftPriority = (index: number, direction: "up" | "down") => {
    const updated = [...items];
    const targetIdx = direction === "up" ? index - 1 : index + 1;
    if (targetIdx < 0 || targetIdx >= items.length) return;

    const temporary = updated[index];
    updated[index] = updated[targetIdx];
    updated[targetIdx] = temporary;
    setItems(updated);
  };

  return (
    <Card className="w-full max-w-4xl mx-auto shadow-md border-zinc-200 dark:border-zinc-800">
      <CardHeader className="bg-gradient-to-r from-zinc-50 to-zinc-100 dark:from-zinc-900 dark:to-zinc-950 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-amber-500 rounded-lg text-white">
            <Milestone className="h-6 w-6" />
          </div>
          <div>
            <CardTitle className="text-2xl font-bold tracking-tight">{roadmapTitle}</CardTitle>
            {description && (
              <CardDescription className="text-zinc-600 dark:text-zinc-400 mt-1">{description}</CardDescription>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6 relative">
        <div className="absolute left-[41px] top-8 bottom-8 w-0.5 bg-zinc-200 dark:bg-zinc-800" />
        <div className="space-y-6">
          {items.map((item, index) => (
            <div key={item.id} className="flex items-start gap-4 relative group" data-testid="roadmap-item-card">
              <div
                className={`z-10 p-2.5 rounded-full border-2 shadow-sm transition-colors ${
                  item.status === "completed"
                    ? "bg-emerald-500 border-emerald-600 text-white"
                    : item.status === "in_progress"
                      ? "bg-amber-500 border-amber-600 text-white"
                      : "bg-white dark:bg-zinc-900 border-zinc-300 dark:border-zinc-700 text-zinc-400"
                }`}
              >
                {item.status === "completed" ? <CheckCircle2 className="h-5 w-5" /> : <BookOpen className="h-5 w-5" />}
              </div>

              <div className="flex-1 bg-zinc-50 dark:bg-zinc-900/50 p-4 rounded-xl border border-zinc-200/60 dark:border-zinc-800/80 transition-shadow group-hover:shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h4 className="font-semibold text-lg text-zinc-900 dark:text-zinc-50 leading-snug">{item.title}</h4>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">by {item.creator}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {item.target_date && (
                      <Badge
                        variant="outline"
                        className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-zinc-600 dark:text-zinc-300"
                      >
                        <Calendar className="h-3.5 w-3.5" />
                        {item.target_date}
                      </Badge>
                    )}
                    <Badge
                      className={
                        item.status === "completed"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
                          : item.status === "in_progress"
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
                            : "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-300"
                      }
                    >
                      {item.status}
                    </Badge>
                  </div>
                </div>

                {item.notes && (
                  <div className="mt-3 flex items-start gap-1.5 text-sm text-zinc-600 dark:text-zinc-400 border-t border-zinc-200 dark:border-zinc-800 pt-2.5">
                    <FileText className="h-4 w-4 mt-0.5 text-zinc-400 shrink-0" />
                    <span>{item.notes}</span>
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity self-center">
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 text-zinc-400 hover:text-zinc-900"
                  disabled={index === 0}
                  onClick={() => shiftPriority(index, "up")}
                  data-testid="move-up-btn"
                  aria-label="Move Up"
                >
                  <MoveUp className="h-4 w-4" />
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  className="h-8 w-8 text-zinc-400 hover:text-zinc-900"
                  disabled={index === items.length - 1}
                  onClick={() => shiftPriority(index, "down")}
                  data-testid="move-down-btn"
                  aria-label="Move Down"
                >
                  <MoveDown className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
