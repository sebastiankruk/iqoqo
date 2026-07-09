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

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import {
  Clock,
  History,
  PlusCircle,
  BookOpen,
  Headphones,
  Music,
  Film,
  Gamepad2,
  Puzzle,
  CheckCircle2,
  Heart,
  ShoppingCart,
  Share2,
  AlertTriangle,
  HelpCircle,
  User,
  ArrowRight,
} from "lucide-react";

interface StatusLog {
  old_status: string | null;
  new_status: string;
  changed_at: string;
  log_type: "creation" | "progress" | "collection";
  operator_name: string;
  category: string;
}

/**
 * Formats status string to title case.
 *
 * @param {string} status - The raw status status string.
 * @returns {string}
 */
function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Component to render individual timeline item with tailored icon and styling.
 *
 * @param {object} props - Component props.
 * @param {StatusLog} props.log - The status log entry.
 * @returns {JSX.Element}
 */
function TimelineItem({ log }: { log: StatusLog }) {
  // Determine appropriate icon, color schemes based on event type
  let IconComponent = Clock;
  let bgClass = "bg-primary/10 text-primary border-primary/20";
  let borderClass = "border-border";
  let badgeColor = "bg-muted text-muted-foreground";
  let description = "";
  let title = "";

  const category = log.category || "text";
  const newStatus = log.new_status;
  const oldStatus = log.old_status;

  if (log.log_type === "creation") {
    IconComponent = PlusCircle;
    bgClass = "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
    borderClass = "border-emerald-500/10 hover:border-emerald-500/30";
    badgeColor = "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
    title = "Added to Collection";
    description = `Initialized progress status to ${formatStatus(newStatus)}.`;
  } else if (log.log_type === "progress") {
    title = "Progress Updated";
    bgClass = "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
    borderClass = "border-blue-500/10 hover:border-blue-500/30";
    badgeColor = "bg-blue-500/10 text-blue-700 dark:text-blue-300";

    // Progress icon depending on media category
    if (category === "text") IconComponent = BookOpen;
    else if (category === "audiobook") IconComponent = Headphones;
    else if (category === "music") IconComponent = Music;
    else if (category === "movie") IconComponent = Film;
    else if (category === "board_game") IconComponent = Gamepad2;
    else if (category === "puzzle") IconComponent = Puzzle;

    description = `Progress marked as ${formatStatus(newStatus)}.`;
  } else {
    // Collection status logs
    title = "Collection Status Updated";
    borderClass = "border-amber-500/10 hover:border-amber-500/30";

    if (newStatus === "available") {
      IconComponent = CheckCircle2;
      bgClass = "bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20";
      badgeColor = "bg-green-500/10 text-green-700 dark:text-green-300";
      description = "Item is now available in your library.";
    } else if (newStatus === "wish_list") {
      IconComponent = Heart;
      bgClass = "bg-pink-500/10 text-pink-600 dark:text-pink-400 border-pink-500/20";
      badgeColor = "bg-pink-500/10 text-pink-700 dark:text-pink-300";
      description = "Item added to your wish list.";
    } else if (newStatus === "ordered") {
      IconComponent = ShoppingCart;
      bgClass = "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20";
      badgeColor = "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300";
      description = "Item has been ordered and is on the way.";
    } else if (newStatus === "lent") {
      IconComponent = Share2;
      bgClass = "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20";
      badgeColor = "bg-amber-500/10 text-amber-700 dark:text-amber-300";
      description = "Loan approved by custodian.";
    } else if (newStatus === "damaged" || newStatus === "lost") {
      IconComponent = AlertTriangle;
      bgClass = "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20";
      borderClass = "border-rose-500/20 hover:border-rose-500/40";
      badgeColor = "bg-rose-500/10 text-rose-700 dark:text-rose-300";
      description = `Item marked as ${formatStatus(newStatus)}.`;
    } else {
      IconComponent = HelpCircle;
      bgClass = "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20";
      description = `Collection status changed to ${formatStatus(newStatus)}.`;
    }
  }

  return (
    <div className="group relative flex gap-x-4 sm:gap-x-6 timeline-event">
      {/* Dynamic colored timeline node */}
      <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border bg-card shadow-sm transition-all duration-300 group-hover:scale-110 sm:h-12 sm:w-12 z-10">
        <div className={`flex h-8 w-8 items-center justify-center rounded-full border ${bgClass}`}>
          <IconComponent className="h-4.5 w-4.5" />
        </div>
      </div>

      {/* Timeline item detail card */}
      <div
        className={`flex-1 rounded-xl border bg-card/60 p-4 shadow-xs transition-all duration-300 group-hover:bg-card group-hover:shadow-sm ${borderClass}`}
      >
        <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
          <h4 className="text-sm font-semibold tracking-tight text-foreground">{title}</h4>
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground bg-secondary/80 px-2 py-0.5 rounded-md self-start sm:self-auto font-medium">
            <User className="h-3 w-3" />
            by {log.operator_name}
          </span>
        </div>

        <p className="mt-2 text-xs text-muted-foreground leading-relaxed">{description}</p>

        {/* Transition details */}
        {oldStatus && (
          <div className="mt-2.5 flex items-center gap-1.5 text-[11px] text-muted-foreground/80">
            <span className="font-mono line-through bg-muted/65 px-1.5 py-0.5 rounded text-muted-foreground/60">
              {formatStatus(oldStatus)}
            </span>
            <ArrowRight className="h-3 w-3 text-muted-foreground/40 shrink-0" />
            <span className={`font-semibold font-mono px-1.5 py-0.5 rounded ${badgeColor}`}>
              {formatStatus(newStatus)}
            </span>
          </div>
        )}

        {/* Date time timestamp */}
        <div className="mt-3 flex items-center gap-1 text-[10px] font-medium tracking-wide uppercase text-muted-foreground/50">
          <Clock className="h-3 w-3" />
          <time>
            {new Intl.DateTimeFormat("en-US", {
              dateStyle: "medium",
              timeStyle: "short",
            }).format(new Date(log.changed_at))}
          </time>
        </div>
      </div>
    </div>
  );
}

/**
 * Item provenance timeline component.
 *
 * @param {object} props - Component props.
 * @param {number} props.itemId - The ID of the item.
 * @returns {JSX.Element | null} The component or null if no logs.
 */
export function ItemProvenanceTimeline({ itemId }: { itemId: number }) {
  const {
    data: logs,
    isLoading,
    error,
  } = useQuery<StatusLog[]>({
    queryKey: ["item", itemId, "logs"],
    queryFn: async () => {
      const res = await apiClient.get(`/items/${itemId}/logs`);
      if (!res.data?.success) throw new Error(res.data?.error ?? "Failed to load history");
      return res.data.data;
    },
    // FRBR ontology boundary: virtual wishlist items (id < 0) have no physical provenance.
    // The backend returns an empty array, but we skip the call entirely to avoid noise in logs.
    enabled: itemId > 0,
  });

  // Virtual wishlist items (UserWorkIntent adapters, id < 0) have no physical timeline.
  // Render a concise empty state instead of showing a loading spinner for a no-op query.
  if (itemId < 0) {
    return (
      <div
        data-testid="virtual-item-timeline-empty"
        className="flex flex-col items-center justify-center py-12 text-center"
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted border border-border/80 shadow-inner">
          <History className="h-6.5 w-6.5 text-muted-foreground" />
        </div>
        <h3 className="mt-4 font-serif text-sm font-bold text-foreground">No physical history</h3>
        <p className="mt-1 text-xs text-muted-foreground max-w-[240px]">
          Wishlist intents do not have a physical timeline, loan history, or condition logs.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center text-destructive text-xs">
        Failed to load item history.
      </div>
    );
  }

  if (!Array.isArray(logs) || logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted border border-border/80 shadow-inner">
          <History className="h-6.5 w-6.5 text-muted-foreground" />
        </div>
        <h3 className="mt-4 font-serif text-sm font-bold text-foreground">No history yet</h3>
        <p className="mt-1 text-xs text-muted-foreground max-w-[240px]">
          Status changes and collections history will appear here.
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="frbr-timeline-log"
      className="relative space-y-6 before:absolute before:inset-y-0 before:left-5 before:-translate-x-px before:w-0.5 before:bg-gradient-to-b before:from-border/80 before:via-border/60 before:to-transparent sm:before:left-[23px] pb-4"
    >
      {logs.map((log, i) => (
        <TimelineItem key={i} log={log} />
      ))}
    </div>
  );
}
