"use client";

import Link from "next/link";
import { BookOpen } from "lucide-react";
import type { Item, ItemStatus } from "@/types/frbr";

const statusDotColor: Record<string, string> = {
  shelf: "bg-chart-3",
  available: "bg-chart-3",
  reading: "bg-primary",
  lent: "bg-accent",
  lost: "bg-destructive",
};

const statusDotTitle: Record<string, string> = {
  shelf: "On Shelf",
  available: "On Shelf",
  reading: "Currently Reading",
  lent: "Lent Out",
  lost: "Lost",
};

/** Individual item card shown in the collection grid. */
export function ItemCard({ item }: { item: Item }) {
  const dotColor = statusDotColor[item.status] ?? "bg-muted";
  const dotTitle = statusDotTitle[item.status] ?? item.status;
  const coverUrl =
    (item.manifestation_meta?.["cover_url"] as string | undefined) ??
    (item.meta?.["cover_url"] as string | undefined);

  return (
    <Link href={`/item/${item.id}`} className="group block">
      <div className="overflow-hidden rounded-lg bg-card shadow-sm ring-1 ring-border/60 transition-all hover:shadow-md hover:ring-border">
        {/* Cover */}
        <div className="relative aspect-[2/3] w-full overflow-hidden bg-secondary">
          {coverUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={coverUrl}
              alt={`Cover of ${item.title}`}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <BookOpen className="h-10 w-10 text-muted-foreground/30" />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-start gap-2 px-3 py-2.5">
          {/* Status dot */}
          <span
            className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotColor}`}
            title={dotTitle}
          />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold leading-snug text-foreground">
              {item.title ?? "Untitled"}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {item.authors?.join(", ") ?? "Unknown author"}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}
