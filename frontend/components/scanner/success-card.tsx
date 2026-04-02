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

import { useState } from "react";
import Image from "next/image";
import { Check, X, BookOpen } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import type { IsbnMeta, ApiResponse } from "@/types/frbr";
import { apiClient } from "@/lib/api/client";

interface SuccessCardProps {
  isbn: string;
  meta: IsbnMeta;
  onDismiss: () => void;
  snappedCover?: File | null;
}

/**
 * SuccessCard component shown after a successful scan.
 * Displays item metadata and provides an option to add it to the library.
 *
 * @param props - Component props
 * @param props.isbn - The barcode that was scanned
 * @param props.meta - The metadata found for the barcode
 * @param props.onDismiss - Function to call when the card is dismissed
 * @param props.snappedCover - Optional file of a cover snapped from video
 * @returns {JSX.Element} The component
 */
export function SuccessCard({ isbn, meta, onDismiss, snappedCover }: SuccessCardProps) {
  const [adding, setAdding] = useState(false);
  const router = useRouter();

  const handleAdd = async () => {
    setAdding(true);
    try {
      // Use the unified format-agnostic scanner endpoint
      const format = meta.Format || meta.format || undefined;
      
      const res = await apiClient.post<ApiResponse<{ item_id: number; manifestation_id: number }>>(`/scan`, {
        barcode: isbn,
        format: format
      });
      const data = res.data.data;
      if (!data) throw new Error(res.data.error || "Failed to ingest item");

      if (snappedCover && data.manifestation_id) {
        const coverFormData = new FormData();
        coverFormData.append("cover", snappedCover);
        try {
          await apiClient.post(`/manifestations/${data.manifestation_id}/cover`, coverFormData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          toast.success(`"${meta.Title}" added with your custom cover!`);
        } catch (e) {
          console.error("Failed to upload snapped cover:", e);
          toast.warning(`"${meta.Title}" added, but cover upload failed.`);
        }
      } else {
        toast.success(`"${meta.Title}" added to your library!`);
      }

      await router.push(`/item/${data.item_id}`);
    } catch (e) {
      toast.error((e as Error).message ?? "Failed to add item");
    } finally {
      setAdding(false);
    }
  };

  const coverUrl: string | null = null;

  return (
    <div className="absolute inset-x-0 bottom-0 z-30 animate-[slide-up_0.4s_cubic-bezier(0.16,1,0.3,1)_forwards]">
      <div className="absolute inset-x-0 -top-24 h-24 bg-gradient-to-t from-black/60 to-transparent" />
      <div className="relative rounded-t-3xl bg-card shadow-[0_-12px_48px_rgba(0,0,0,0.3)]">
        <div className="flex items-center justify-between px-6 pt-5 pb-4">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-chart-3">
              <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />
            </span>
            <span className="text-sm font-semibold text-foreground">Item Found</span>
          </div>
          <button onClick={onDismiss} className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary hover:bg-muted">
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>

        <div className="flex gap-4 px-6 pb-5">
          <div className="relative h-28 w-20 shrink-0 overflow-hidden rounded-lg shadow-lg bg-secondary">
            {coverUrl ? (
              <Image src={coverUrl} alt={meta.Title} fill unoptimized className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full items-center justify-center">
                <div className="flex flex-col items-center gap-1.5 text-muted-foreground/30">
                  <BookOpen className="h-8 w-8" />
                  <span className="text-[10px] font-bold uppercase tracking-widest">iQoQo</span>
                </div>
              </div>
            )}
          </div>

          <div className="flex min-w-0 flex-col justify-center">
            <h3 className="font-serif text-lg font-bold leading-tight text-foreground">{meta.Title}</h3>
            {meta.Authors && meta.Authors.length > 0 && (
              <p className="mt-0.5 text-sm text-muted-foreground">{meta.Authors.join(", ")}</p>
            )}
            {isbn && <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">Barcode: {isbn}</p>}
          </div>
        </div>

        <div className="flex gap-3 border-t border-border px-6 py-4">
          <button onClick={handleAdd} disabled={adding} className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary py-3.5 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-60">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M9 3v12M3 9h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" /></svg>
            {adding ? "Adding…" : "Add to Library"}
          </button>
          <button onClick={onDismiss} className="flex items-center justify-center rounded-xl border border-border bg-card px-5 py-3.5 text-sm font-semibold hover:bg-secondary">
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
