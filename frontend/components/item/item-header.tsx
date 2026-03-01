"use client";

import { useState } from "react";
import { Calendar, BookOpen, Tag, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api/client";
import { useManifestationWithPolling } from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";

/** Title, authors, year, page count, and tag badges for an item. */
export function ItemHeader({ item: initialItem }: { item: Item }) {
  const { item, setItem } = useManifestationWithPolling(initialItem);
  const [isRequesting, setIsRequesting] = useState(false);

  const work = item.work;
  const meta = item.manifestation_meta ?? {};
  const tags = (meta["tags"] as string[] | undefined) ?? [];
  const year = meta["Year"] as string | undefined;
  const pages = meta["Pages"] as string | undefined;
  const isPending = item.cover_status === 'pending';

  const handleRegenerate = async () => {
    if (!item.manifestation_id) return;
    setIsRequesting(true);
    try {
      await apiClient.post(`/manifestations/${item.manifestation_id}/regenerate-cover`);
      setItem((prev) => ({
        ...prev,
        cover_status: 'pending'
      }));
    } catch (error) {
      console.error("Failed to schedule regeneration:", error);
    } finally {
      setIsRequesting(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h1 className="text-balance font-serif text-2xl font-bold leading-tight text-foreground sm:text-3xl">
          {work?.title ?? item.title ?? "Untitled"}
        </h1>
        {!!meta["Subtitle"] && (
          <h2 className="font-serif text-base font-light text-muted-foreground sm:text-lg">
            {meta["Subtitle"] as string}
          </h2>
        )}
      </div>

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRegenerate}
          disabled={isPending || isRequesting}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${isPending ? 'animate-spin' : ''}`} />
          {isPending ? "Generating..." : "Regenerate Cover"}
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm text-muted-foreground">
        {work?.authors && work.authors.length > 0 && (
          <span className="font-medium text-foreground">
            {work.authors.join(", ")}
          </span>
        )}
        {year && (
          <>
            <span className="text-border">&bull;</span>
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {year}
            </span>
          </>
        )}
        {pages && (
          <>
            <span className="text-border">&bull;</span>
            <span className="flex items-center gap-1">
              <BookOpen className="h-3.5 w-3.5" />
              {pages} pages
            </span>
          </>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {tags.map((tag) => (
            <span
              key={tag}
              className="flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground"
            >
              <Tag className="h-3 w-3" />
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="h-px bg-border" />
    </div>
  );
}
