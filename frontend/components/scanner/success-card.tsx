"use client";

import { useState } from "react";
import Image from "next/image";
import { Check, X, BookOpen } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import type { IsbnMeta } from "@/types/frbr";
import { apiClient } from "@/lib/api/client";

interface SuccessCardProps {
  isbn: string;
  meta: IsbnMeta;
  onDismiss: () => void;
}

/** Slide-up result card shown after a successful barcode scan. */
export function SuccessCard({ isbn, meta, onDismiss }: SuccessCardProps) {
  const [adding, setAdding] = useState(false);
  const router = useRouter();

  const handleAdd = async () => {
    setAdding(true);
    try {
      const res = await apiClient.post<{ item_id: number }>(
        `/item/${isbn}`,
        meta
      );
      toast.success(`"${meta.Title}" added to your library!`);
      router.push(`/item/${res.data.item_id}`);
    } catch (e) {
      toast.error((e as Error).message ?? "Failed to add item");
      setAdding(false);
    }
  };

  const coverUrl: string | null = null; // Future: resolve cover from ISBN

  return (
    <div className="absolute inset-x-0 bottom-0 z-30 animate-[slide-up_0.4s_cubic-bezier(0.16,1,0.3,1)_forwards]">
      {/* Gradient backdrop */}
      <div className="absolute inset-x-0 -top-24 h-24 bg-gradient-to-t from-black/60 to-transparent" />

      <div className="relative rounded-t-3xl bg-card shadow-[0_-12px_48px_rgba(0,0,0,0.3)]">
        {/* Success header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-chart-3">
              <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />
            </span>
            <span className="text-sm font-semibold text-foreground">
              Book Found
            </span>
          </div>
          <button
            onClick={onDismiss}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary transition-colors hover:bg-muted"
            aria-label="Dismiss result"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>

        {/* Book info */}
        <div className="flex gap-4 px-6 pb-5">
          <div className="relative h-28 w-20 shrink-0 overflow-hidden rounded-lg shadow-lg bg-secondary">
            {coverUrl ? (
              <Image
                src={coverUrl}
                alt={meta.Title}
                fill
                unoptimized
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-center justify-center">
                <BookOpen className="h-8 w-8 text-muted-foreground/30" />
              </div>
            )}
          </div>

          <div className="flex min-w-0 flex-col justify-center">
            <h3 className="font-serif text-lg font-bold leading-tight text-foreground">
              {meta.Title}
            </h3>
            {meta.Authors && meta.Authors.length > 0 && (
              <p className="mt-0.5 text-sm text-muted-foreground">
                {meta.Authors.join(", ")}
              </p>
            )}
            {isbn && (
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                ISBN: {isbn}
              </p>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 border-t border-border px-6 py-4">
          <button
            onClick={handleAdd}
            disabled={adding}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary py-3.5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 active:scale-[0.98] disabled:opacity-60"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path
                d="M9 3v12M3 9h12"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
            {adding ? "Adding…" : "Add to Library"}
          </button>
          <button
            onClick={onDismiss}
            className="flex items-center justify-center rounded-xl border border-border bg-card px-5 py-3.5 text-sm font-semibold text-foreground transition-colors hover:bg-secondary active:scale-[0.98]"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
