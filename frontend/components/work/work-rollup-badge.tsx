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

import { Bookmark, CheckCircle2, Clock, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";

const STATUS_KEY_MAP: Record<string, string> = {
  read: "statusRead",
  listened: "statusListened",
  watched: "statusWatched",
  played: "statusPlayed",
  built: "statusBuilt",
  reading: "statusReading",
  listening: "statusListening",
  watching: "statusWatching",
  playing: "statusPlaying",
  building: "statusBuilding",
  want_to_read: "statusWant",
  want_to_listen: "statusWant",
  want_to_watch: "statusWant",
  want_to_play: "statusWant",
  want_to_build: "statusWant",
  dnf: "statusDnf",
};

const COMPLETED_STATUSES = new Set(["read", "listened", "watched", "played", "built"]);
const ACTIVE_STATUSES = new Set(["reading", "listening", "watching", "playing", "building"]);

interface WorkRollupBadgeProps {
  status?: string | null;
  viaOtherEdition?: boolean;
}

/**
 * Localized badge rendering a user's rolled-up Work consumption status.
 *
 * @param props - Rollup badge properties.
 * @returns Badge element or null when unstarted / unauthenticated.
 */
export function WorkRollupBadge({ status, viaOtherEdition = false }: WorkRollupBadgeProps) {
  const t = useTranslations("WorkRollup");
  if (!status) {
    return null;
  }

  const normalized = status.trim().toLowerCase();
  const messageKey = STATUS_KEY_MAP[normalized];
  if (!messageKey) {
    return null;
  }

  const baseLabel = t(messageKey);
  const label =
    viaOtherEdition && COMPLETED_STATUSES.has(normalized) ? t("otherEditionLabel", { label: baseLabel }) : baseLabel;

  const isCompleted = COMPLETED_STATUSES.has(normalized);
  const isActive = ACTIVE_STATUSES.has(normalized);
  const isDnf = normalized === "dnf";

  const toneClass = isCompleted
    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
    : isActive
      ? "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300"
      : isDnf
        ? "border-destructive/30 bg-destructive/10 text-destructive"
        : "border-border bg-secondary text-secondary-foreground";

  return (
    <Badge
      variant="outline"
      data-testid="work-rollup-badge"
      className={`gap-1.5 px-2.5 py-0.5 text-xs font-semibold ${toneClass}`}
    >
      {isCompleted ? (
        <CheckCircle2 className="h-3 w-3" />
      ) : isActive ? (
        <Clock className="h-3 w-3" />
      ) : isDnf ? (
        <XCircle className="h-3 w-3" />
      ) : (
        <Bookmark className="h-3 w-3" />
      )}
      <span>{label}</span>
    </Badge>
  );
}
