"use client";

import { BookOpen } from "lucide-react";
import { useItems } from "@/lib/api/hooks";
import Link from "next/link";

/**
 * "Current Context" section – shows items with status "reading".
 * Falls back to a placeholder card if no active items found.
 */
export function CurrentContext() {
  const { data, isLoading } = useItems(1, 10);

  const readingItems =
    data?.data?.filter((item) => item.status === "reading") ?? [];

  if (isLoading) {
    return (
      <section aria-label="Currently active items">
        <h2 className="mb-5 font-serif text-xl font-bold text-foreground">
          Current Context
        </h2>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-40 animate-pulse rounded-xl bg-card shadow-sm"
            />
          ))}
        </div>
      </section>
    );
  }

  if (readingItems.length === 0) {
    return (
      <section aria-label="Currently active items">
        <div className="mb-5 flex items-center gap-2">
          <h2 className="font-serif text-xl font-bold text-foreground">
            Current Context
          </h2>
        </div>
        <div className="rounded-xl border border-dashed border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No items currently in progress.{" "}
            <Link href="/collection" className="text-accent underline-offset-2 hover:underline">
              Browse your collection
            </Link>{" "}
            to start reading.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Currently active items">
      <div className="mb-5 flex items-center gap-2">
        <h2 className="font-serif text-xl font-bold text-foreground">
          Current Context
        </h2>
        <span className="rounded-full bg-accent/10 px-2.5 py-0.5 text-xs font-semibold text-accent">
          {readingItems.length} active
        </span>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {readingItems.map((item) => (
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
                    {item.title ?? "Untitled"}
                  </h3>
                  {item.authors && item.authors.length > 0 && (
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {item.authors.join(", ")}
                    </p>
                  )}
                  <div className="mt-3 flex items-center gap-2">
                    <span className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-1 text-xs font-semibold text-accent">
                      Reading
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}
