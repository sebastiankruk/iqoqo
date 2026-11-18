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

"use client";

import * as React from "react";
import { Clock } from "lucide-react";
import { useTranslations } from "next-intl";
import type { Item } from "@/types/frbr";
import { useLogReadingSession } from "@/lib/api/hooks";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ReadingDurationCardProps {
  item: Item;
  isOwner: boolean;
}

/**
 * Format total minutes into a human-readable hours and minutes string.
 *
 * @param totalMinutes - Total reading minutes
 * @returns Formatted duration string (e.g. "2h 0m" or "45m")
 */
function formatDurationMinutes(totalMinutes: number): string {
  const safeMinutes = Math.max(0, Math.floor(totalMinutes));
  const hours = Math.floor(safeMinutes / 60);
  const mins = safeMinutes % 60;
  if (hours > 0) {
    return `${hours}h ${mins}m`;
  }
  return `${mins}m`;
}

/**
 * Compact FRBR Item-scoped reading duration summary and quick-log modal trigger.
 *
 * @param props - Component props containing the item and ownership flag
 * @returns Reading duration card or null when not applicable
 */
export function ReadingDurationCard({ item, isOwner }: ReadingDurationCardProps) {
  const t = useTranslations("ItemDetail.readingDuration");
  const logSession = useLogReadingSession(item.id);

  const [isOpen, setIsOpen] = React.useState(false);
  const [durationMinutes, setDurationMinutes] = React.useState("30");
  const [pagesRead, setPagesRead] = React.useState("");
  const [note, setNote] = React.useState("");

  const summary = item.reading_duration_summary;
  const totalMinutes = summary?.total_minutes ?? 0;
  const sessionsCount = summary?.sessions_count ?? 0;
  const elapsedDays = summary?.elapsed_days ?? null;

  const shouldShow =
    isOwner && (item.status === "reading" || item.status === "read" || totalMinutes > 0 || sessionsCount > 0);

  if (!shouldShow) {
    return null;
  }

  const formattedDuration = formatDurationMinutes(totalMinutes);
  const baseSummary =
    sessionsCount === 1
      ? t("summaryOne", { duration: formattedDuration })
      : t("summary", { duration: formattedDuration, count: sessionsCount });
  const daysSuffix =
    elapsedDays === null ? "" : elapsedDays === 1 ? t("elapsedDaysOne") : t("elapsedDays", { days: elapsedDays });
  const summaryText = baseSummary + daysSuffix;

  const handleQuickLog = (minutes: number) => {
    logSession.mutate(
      { duration_minutes: minutes },
      {
        onSuccess: () => {
          setIsOpen(false);
        },
      }
    );
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsedMinutes = parseInt(durationMinutes, 10);
    if (isNaN(parsedMinutes) || parsedMinutes < 1 || parsedMinutes > 1440) {
      return;
    }
    const parsedPages = pagesRead.trim() ? parseInt(pagesRead, 10) : undefined;
    logSession.mutate(
      {
        duration_minutes: parsedMinutes,
        pages_read: parsedPages && !isNaN(parsedPages) && parsedPages > 0 ? parsedPages : undefined,
        note: note.trim() ? note.trim() : undefined,
      },
      {
        onSuccess: () => {
          setPagesRead("");
          setNote("");
          setIsOpen(false);
        },
      }
    );
  };

  return (
    <div className="w-full rounded-lg border bg-card p-3 text-card-foreground shadow-sm">
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-1">
        <Clock className="h-3.5 w-3.5" aria-hidden="true" />
        <span>{t("title")}</span>
      </div>
      <p className="text-sm font-medium text-foreground mb-2.5">{summaryText}</p>
      <Button type="button" variant="outline" size="sm" className="w-full" onClick={() => setIsOpen(true)}>
        {t("logButton")}
      </Button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("dialogTitle")}</DialogTitle>
            <DialogDescription>{t("dialogDescription")}</DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">{t("quickPresets")}</p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  disabled={logSession.isPending}
                  onClick={() => handleQuickLog(15)}
                >
                  +15m
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  disabled={logSession.isPending}
                  onClick={() => handleQuickLog(30)}
                >
                  +30m
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  disabled={logSession.isPending}
                  onClick={() => handleQuickLog(60)}
                >
                  +1h
                </Button>
              </div>
            </div>

            <form onSubmit={handleCustomSubmit} className="space-y-3">
              <div className="space-y-1">
                <label htmlFor="reading-duration-minutes" className="text-sm font-medium leading-none">
                  {t("durationLabel")}
                </label>
                <input
                  id="reading-duration-minutes"
                  type="number"
                  min={1}
                  max={1440}
                  required
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={durationMinutes}
                  onChange={e => setDurationMinutes(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="reading-pages-read" className="text-sm font-medium leading-none">
                  {t("pagesLabel")}
                </label>
                <input
                  id="reading-pages-read"
                  type="number"
                  min={1}
                  max={5000}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={pagesRead}
                  onChange={e => setPagesRead(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="reading-session-note" className="text-sm font-medium leading-none">
                  {t("noteLabel")}
                </label>
                <input
                  id="reading-session-note"
                  type="text"
                  maxLength={280}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={note}
                  onChange={e => setNote(e.target.value)}
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsOpen(false)}>
                  {t("cancel")}
                </Button>
                <Button type="submit" disabled={logSession.isPending}>
                  {logSession.isPending ? t("saving") : t("submit")}
                </Button>
              </DialogFooter>
            </form>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
