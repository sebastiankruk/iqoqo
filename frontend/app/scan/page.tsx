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

import { useState, useCallback, useRef } from "react";
import { TopBar } from "@/components/scanner/top-bar";
import { Viewfinder } from "@/components/scanner/viewfinder";
import { BottomSheet } from "@/components/scanner/bottom-sheet";
import { SuccessCard } from "@/components/scanner/success-card";
import { useAddManualItem } from "@/lib/api/hooks";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import type { IsbnMeta } from "@/types/frbr";

export default function ScanPage() {
  const [result, setResult] = useState<{ isbn: string; meta: IsbnMeta } | null>(null);
  const [showManual, setShowManual] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const addManualMutation = useAddManualItem();
  const router = useRouter();

  const handleFound = useCallback((isbn: string, meta: IsbnMeta) => {
    setResult({ isbn, meta });
  }, []);

  const handleDismiss = useCallback(() => {
    setResult(null);
  }, []);

  const handleManualSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const payload = {
      Title: formData.get("title")?.toString() || "Unknown",
      Authors: [formData.get("author")?.toString() || "Unknown"],
      Format: formData.get("format")?.toString() || "text",
    };

    addManualMutation.mutate(payload, {
      onSuccess: (data) => {
        toast.success(`"${payload.Title}" added to your library!`);
        router.push(`/item/${data.item_id}`);
      },
      onError: (err) => {
        toast.error((err as Error).message || "Failed to add item manually");
      },
    });
  };

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden bg-black">
      <video ref={videoRef} playsInline muted autoPlay aria-hidden="true" className="absolute inset-0 z-0 h-full w-full object-cover" />

      <TopBar />
      <Viewfinder />

      {!result && !showManual && <BottomSheet videoRef={videoRef} onFound={handleFound} />}
      {result && <SuccessCard isbn={result.isbn} meta={result.meta} onDismiss={handleDismiss} />}

      {/* Manual Entry Trigger & Form */}
      {!result && !showManual && (
        <div className="absolute bottom-32 w-full flex justify-center z-10">
          <button onClick={() => setShowManual(true)} className="rounded-full bg-secondary px-6 py-2.5 text-sm font-semibold text-secondary-foreground shadow-lg hover:bg-secondary/80">
            Cannot find barcode? Enter Manually
          </button>
        </div>
      )}

      {showManual && (
        <div className="absolute inset-x-0 bottom-0 z-40 bg-card rounded-t-3xl shadow-2xl p-6 pb-12 animate-[slide-up_0.3s_ease-out_forwards]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold font-serif text-foreground">Manual Entry</h2>
            <button onClick={() => setShowManual(false)} className="text-muted-foreground hover:text-foreground">Cancel</button>
          </div>
          <form onSubmit={handleManualSubmit} className="flex flex-col gap-4">
            <div>
              <label className="text-sm font-medium text-foreground block mb-1">Title</label>
              <input name="title" required className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary" placeholder="E.g. The Hobbit" />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground block mb-1">Author / Creator</label>
              <input name="author" required className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary" placeholder="E.g. J.R.R. Tolkien" />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground block mb-1">Format</label>
              <select name="format" className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary">
                <option value="text">Book (Text)</option>
                <option value="sound">CD/Vinyl (Audio)</option>
                <option value="video">DVD/BluRay (Video)</option>
                <option value="game">Board Game</option>
              </select>
            </div>
            <button type="submit" disabled={addManualMutation.isPending} className="mt-2 w-full rounded-lg bg-primary py-3 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50">
              {addManualMutation.isPending ? "Adding..." : "Add to Library"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
