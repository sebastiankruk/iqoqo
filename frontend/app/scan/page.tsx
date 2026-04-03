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
/**
 * The scan page for capturing barcodes, covers, and manual entry.
 *
 * @module app/scan/page
 */
"use client";

import { useState, useCallback, useRef } from "react";
import { TopBar } from "@/components/scanner/top-bar";
import { Viewfinder } from "@/components/scanner/viewfinder";
import { BottomSheet } from "@/components/scanner/bottom-sheet";
import { SuccessCard } from "@/components/scanner/success-card";
import { ManualEntryForm } from "@/components/scanner/manual-entry-form";
import type { ManualEntryData } from "@/components/scanner/manual-entry-form";
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
  const [activeFormat, setActiveFormat] = useState<"book" | "cd" | "vinyl">("book");
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

  const handleManualSubmit = async (data: ManualEntryData) => {
    const payload = {
      Title: data.title || "Unknown",
      Authors: data.authors ? data.authors.split(",").map(a => a.trim()) : ["Unknown"],
      Format: data.format === "book" ? "text" : "sound", // Map UI format to API format
      ISBN: data.identifier || undefined,
      PublicationDate: data.year || undefined,
      Publisher: data.publisher || undefined,
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
      
      {/* Format Toggle */}
      {!result && !showManual && (
        <div className="absolute top-20 inset-x-0 z-30 flex justify-center">
          <div className="inline-flex rounded-full bg-black/40 backdrop-blur-md p-1 border border-white/10">
            {(["book", "cd", "vinyl"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setActiveFormat(f)}
                className={`rounded-full px-4 py-1.5 text-[10px] font-bold uppercase tracking-widest transition-all ${
                  activeFormat === f 
                    ? "bg-primary text-primary-foreground" 
                    : "text-white/70 hover:text-white"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      )}

      {!result && !showManual && scannerTab === "barcode" && (
        <Viewfinder isScanning={scannerActive} format={activeFormat} />
      )}

      {!result && !showManual && (
        <BottomSheet
          videoRef={videoRef}
          onFound={handleFound}
          onScannerStateChange={setScannerActive}
          onTabChange={setScannerTab}
          onExtractComplete={handleExtractComplete}
          onShowManualForm={() => setShowManual(true)}
          format={activeFormat}
        />
      )}
      {result && (
        <SuccessCard isbn={result.isbn} meta={result.meta} onDismiss={handleDismiss} snappedCover={snappedCover} />
      )}

      {showManual && (
        <div className="absolute inset-x-0 bottom-0 z-40 bg-card rounded-t-3xl shadow-2xl pb-12 animate-[slide-up_0.3s_ease-out_forwards]">
          <ManualEntryForm 
            onSubmit={handleManualSubmit}
            onCancel={() => setShowManual(false)}
            initialTitle={title}
            initialAuthors={author}
            initialFormat={activeFormat}
          />
        </div>
      )}
    </div>
  );
}
