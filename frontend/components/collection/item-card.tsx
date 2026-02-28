"use client";

import Link from "next/link";
import Image from "next/image";
import { BookOpen, Loader2 } from "lucide-react";
import type { Item, ItemStatus } from "@/types/frbr";

const statusDotColor: Record<ItemStatus, string> = {
  available: "bg-chart-3",
  wish_list: "bg-primary",
  lent: "bg-accent",
  lost: "bg-destructive",
  reading: "bg-green-500",
  read: "bg-blue-500",
};

const statusDotTitle: Record<ItemStatus, string> = {
  available: "On Shelf",
  wish_list: "On Wish List",
  lent: "Lent Out",
  lost: "Lost",
  reading: "Reading",
  read: "Read",
};

interface ItemCardProps {
  item: Item;
  variant?: "vertical" | "horizontal";
}

type ItemWithCoverFields = Item & {
  cover_path?: string;
  cover_status?: string;
};

/** Individual item card shown in the collection grid. */
export function ItemCard({ item, variant = "vertical" }: ItemCardProps) {
  const dotColor = statusDotColor[item.status] ?? "bg-muted";
  const dotTitle = statusDotTitle[item.status] ?? item.status;

  // Resolve cover URL: Local > Legacy Meta > Placeholder
  const itemWithCoverFields = item as ItemWithCoverFields;
  const coverUrl = itemWithCoverFields.cover_path
    ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"}${itemWithCoverFields.cover_path}`
    : (item.manifestation_meta?.["cover_url"] as string | undefined) ??
      (item.meta?.["cover_url"] as string | undefined);
  const coverSource = item.manifestation_meta?.["cover_source"];

  const isProcessing = itemWithCoverFields.cover_status === "processing";
  const isGenerated =
    itemWithCoverFields.cover_status === "ready" &&
    typeof coverSource === "string" &&
    coverSource.includes("generated");

  const title = item.title ?? "Untitled";
  const authors = item.authors?.join(", ") ?? "Unknown author";

  if (variant === "horizontal") {
    return (
        <Link
            key={item.id}
            href={`/item/${item.id}`}
            className="group overflow-hidden rounded-xl bg-card shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="flex h-full p-5">
              <div className="flex flex-1 flex-col justify-between">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      Book
                    </span>
                  </div>
                  <h3 className="font-serif text-lg font-bold leading-snug text-card-foreground">
                    {title}
                  </h3>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {authors}
                  </p>
                  <div className="mt-3 flex items-center gap-2">
                    <span className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-1 text-xs font-semibold text-accent">
                      {dotTitle}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </Link>
    );
  }

  return (
    <Link href={`/item/${item.id}`} className="group block">
      <div className="overflow-hidden rounded-lg bg-card shadow-sm ring-1 ring-border/60 transition-all hover:shadow-md hover:ring-border">
        {/* Cover */}
        <div className="relative aspect-[2/3] w-full overflow-hidden bg-secondary">
          {isProcessing ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 bg-muted/50 p-4 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="text-xs font-medium text-muted-foreground">Generating Cover...</span>
            </div>
          ) : coverUrl ? (
            <Image
              src={coverUrl}
              alt={`Cover of ${title}`}
              fill
              sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
              unoptimized
              className={`object-cover transition-transform duration-300 group-hover:scale-105 ${isGenerated ? "sepia-[.15]" : ""}`}
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
              {title}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {authors}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}
