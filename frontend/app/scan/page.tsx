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
import type { FormEvent } from "react";
import { TopBar } from "@/components/scanner/top-bar";
import { Viewfinder } from "@/components/scanner/viewfinder";
import { BottomSheet } from "@/components/scanner/bottom-sheet";
import { SuccessCard } from "@/components/scanner/success-card";
import { useAddManualItem } from "@/lib/api/hooks";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import type { IsbnMeta } from "@/types/frbr";
import { apiClient } from "@/lib/api/client";

/**
 * The scan page component for scanning barcodes and manual entry.
 *
 * @returns {JSX.Element} The ScanPage component
 */
export default function ScanPage() {
  const [result, setResult] = useState<{ isbn: string; meta: IsbnMeta } | null>(null);
  const [showManual, setShowManual] = useState(false);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [scannerActive, setScannerActive] = useState(false);
  const [scannerTab, setScannerTab] = useState<"barcode" | "cover" | "manual">("barcode");
  const [snappedCover, setSnappedCover] = useState<File | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const addManualMutation = useAddManualItem();
  const router = useRouter();

  const handleFound = useCallback((isbn: string, meta: IsbnMeta) => {
    setResult({ isbn, meta });
  }, []);

  const handleDismiss = useCallback(() => {
    setResult(null);
  }, []);

  const handleExtractComplete = useCallback((data: { Title?: string; Authors?: string[] }, file?: File) => {
    setTitle(data.Title || "");
    setAuthor(data.Authors?.join(", ") || "");
    if (file) setSnappedCover(file);
    setShowManual(true);
    toast.success("Cover metadata extracted! Please review.");
  }, []);

  const handleManualSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const payload = {
      Title: formData.get("title")?.toString() || "Unknown",
      Authors: [formData.get("author")?.toString() || "Unknown"],
      Format: formData.get("format")?.toString() || "text",
      ISBN: formData.get("isbn")?.toString() || undefined,
      PublicationDate: formData.get("pubdate")?.toString() || undefined,
      Description: formData.get("description")?.toString() || undefined,
    };

    addManualMutation.mutate(payload, {
      onSuccess: async response => {
        const item = response.data;
        if (item && snappedCover && item.manifestation_id) {
          const coverFormData = new FormData();
          coverFormData.append("cover", snappedCover);
          try {
            await apiClient.post(`/manifestations/${item.manifestation_id}/cover`, coverFormData, {
              headers: { "Content-Type": "multipart/form-data" },
            });
            toast.success(`"${payload.Title}" added with your custom cover!`);
          } catch (e) {
            console.error("Failed to upload captured cover:", e);
            toast.warning(`"${payload.Title}" added, but cover upload failed.`);
          }
        } else {
          toast.success(`"${payload.Title}" added to your library!`);
        }

        if (response.data?.item_id) {
          router.push(`/item/${response.data.item_id}`);
        }
      },
      onError: err => {
        toast.error((err as Error).message || "Failed to add item manually");
      },
    });
  };

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden bg-black">
      <video
        ref={videoRef}
        playsInline
        muted
        autoPlay
        aria-hidden="true"
        className="absolute inset-0 z-0 h-full w-full object-cover"
      />

      <TopBar />
      {!result && !showManual && scannerTab === "barcode" && <Viewfinder isScanning={scannerActive} />}

      {!result && !showManual && (
        <BottomSheet
          videoRef={videoRef}
          onFound={handleFound}
          onScannerStateChange={setScannerActive}
          onTabChange={setScannerTab}
          onExtractComplete={handleExtractComplete}
          onShowManualForm={() => setShowManual(true)}
        />
      )}
      {result && (
        <SuccessCard isbn={result.isbn} meta={result.meta} onDismiss={handleDismiss} snappedCover={snappedCover} />
      )}

      {showManual && (
        <div className="absolute inset-x-0 bottom-0 z-40 bg-card rounded-t-3xl shadow-2xl p-6 pb-12 animate-[slide-up_0.3s_ease-out_forwards]">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold font-serif text-foreground">Manual Entry</h2>
            <button onClick={() => setShowManual(false)} className="text-muted-foreground hover:text-foreground">
              Cancel
            </button>
          </div>
          <form onSubmit={handleManualSubmit} className="flex flex-col gap-4">
            <div>
              <label htmlFor="manual-title" className="text-sm font-medium text-foreground block mb-1">
                Title
              </label>
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                id="manual-title"
                name="title"
                required
                className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary"
                placeholder="E.g. The Hobbit"
              />
            </div>
            <div>
              <label htmlFor="manual-author" className="text-sm font-medium text-foreground block mb-1">
                Author / Creator
              </label>
              <input
                value={author}
                onChange={e => setAuthor(e.target.value)}
                id="manual-author"
                name="author"
                required
                className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary"
                placeholder="E.g. J.R.R. Tolkien"
              />
            </div>
            <div>
              <label htmlFor="manual-isbn" className="text-sm font-medium text-foreground block mb-1">
                ISBN (Optional)
              </label>
              <input
                id="manual-isbn"
                name="isbn"
                className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary"
                placeholder="978-..."
              />
            </div>
            <div className="flex gap-4">
              <div className="flex-1">
                <label htmlFor="manual-pubdate" className="text-sm font-medium text-foreground block mb-1">
                  Publish Date
                </label>
                <input
                  type="date"
                  id="manual-pubdate"
                  name="pubdate"
                  className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary text-foreground"
                />
              </div>
              <div className="flex-1">
                <label htmlFor="manual-format" className="text-sm font-medium text-foreground block mb-1">
                  Format
                </label>
                <select
                  id="manual-format"
                  name="format"
                  className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="text">Book (Text)</option>
                  <option value="sound">CD/Vinyl</option>
                  <option value="video">DVD/BluRay</option>
                  <option value="game">Board Game</option>
                </select>
              </div>
            </div>
            <div>
              <label htmlFor="manual-description" className="text-sm font-medium text-foreground block mb-1">
                Description (Optional)
              </label>
              <textarea
                id="manual-description"
                name="description"
                rows={3}
                className="w-full rounded-lg border border-border bg-background px-4 py-2.5 outline-none focus:ring-2 focus:ring-primary resize-none"
                placeholder="Brief summary..."
              ></textarea>
            </div>
            <button
              type="submit"
              disabled={addManualMutation.isPending}
              className="mt-2 w-full rounded-lg bg-primary py-3 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {addManualMutation.isPending ? "Adding..." : "Add to Library"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
