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
import { DisambiguationSheet } from "@/components/scanner/disambiguation-sheet";
import { ManualEntryForm } from "@/components/scanner/manual-entry-form";
import type { ManualEntryData } from "@/components/scanner/manual-entry-form";
import { ScannerErrorBoundary } from "@/components/scanner/error-boundary";
import { useAddManualItem } from "@/lib/api/hooks";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import type { IsbnMeta, ScanFormat } from "@/types/frbr";
import { apiClient } from "@/lib/api/client";
import { mapFormatToApi } from "@/lib/media";

/**
 * The scan page component for scanning barcodes and manual entry.
 *
 * @returns {JSX.Element} The ScanPage component
 */
export default function ScanPage() {
  const [result, setResult] = useState<{ isbn: string; meta: IsbnMeta } | null>(null);
  const [candidates, setCandidates] = useState<{ isbn: string; items: IsbnMeta[] } | null>(null);
  const [showManual, setShowManual] = useState(false);
  const [initialIdentifier, setInitialIdentifier] = useState("");
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [scannerActive, setScannerActive] = useState(false);
  const [scannerTab, setScannerTab] = useState<"barcode" | "cover" | "manual">("barcode");
  const [activeFormat, setActiveFormat] = useState<ScanFormat>("book");
  const [snappedCover, setSnappedCover] = useState<File | null>(null);
  const [hasTorch, setHasTorch] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const addManualMutation = useAddManualItem();
  const router = useRouter();

  const handleFound = useCallback((isbn: string, meta: IsbnMeta) => {
    // Prefer the backend-normalized identifier/barcode if available
    const canonicalId = meta.identifier || meta.barcode || meta.isbn || isbn;

    if (meta.candidates && meta.candidates.length > 1) {
      setCandidates({ isbn: canonicalId, items: meta.candidates });
    } else {
      setResult({ isbn: canonicalId, meta });
    }
  }, []);

  const handleDismiss = useCallback(() => {
    setResult(null);
    setCandidates(null);
  }, []);

  const handleExtractComplete = useCallback((data: { Title?: string; Authors?: string[] }, file?: File) => {
    setTitle(data.Title || "");
    setAuthor(data.Authors?.join(", ") || "");
    if (file) setSnappedCover(file);
    setInitialIdentifier("");
    setShowManual(true);
    toast.success("Cover metadata extracted! Please review.");
  }, []);

  const handleShowManualForm = useCallback((isbn?: string) => {
    setInitialIdentifier(isbn || "");
    setShowManual(true);
  }, []);

  const handleExtractionFailure = useCallback(
    (ean: string) => {
      handleShowManualForm(ean);
      toast.info("Switching to manual entry...");
    },
    [handleShowManualForm]
  );

  const handleManualSubmit = async (data: ManualEntryData) => {
    const authors = data.authors
      ? data.authors
          .split(",")
          .map(a => a.trim())
          .filter(Boolean)
      : ["Unknown"];

    let explicitDate = data.year || undefined;
    if (explicitDate && /^\d{4}$/.test(explicitDate)) {
      explicitDate = `${explicitDate}-01-01`;
    }

    const apiFormat = mapFormatToApi(data.format);

    const payload = {
      Title: data.title || "Unknown",
      Authors: authors.length > 0 ? authors : ["Unknown"],
      Format: apiFormat,
      ISBN: data.identifier || undefined,
      PublicationDate: explicitDate,
      Publisher: data.publisher || undefined,
    };

    addManualMutation.mutate(payload, {
      onSuccess: async response => {
        const item = response.data;
        const coverToUpload = data.coverFile || snappedCover;

        if (item && coverToUpload && item.manifestation_id) {
          const coverFormData = new FormData();
          coverFormData.append("cover", coverToUpload);
          const isSnapped = coverToUpload === snappedCover;
          coverFormData.append("source", isSnapped ? "scanner_camera" : "user_upload");
          try {
            await apiClient.post(`/manifestations/${item.manifestation_id}/cover`, coverFormData, {
              headers: { "Content-Type": "multipart/form-data" },
            });
            toast.success(`"${payload.Title}" added with your custom cover!`);
          } catch (e) {
            const errMsg = (e as Error)?.message || "Cover upload failed";
            console.error("Failed to upload cover:", e);
            toast.error(`"${payload.Title}" added, but cover upload failed: ${errMsg}`);
          }
        } else {
          toast.success(`"${payload.Title}" added to your library!`);
        }

        if (response.data?.item_id) {
          router.push(`/item?id=${response.data.item_id}`);
        }
      },
      onError: err => {
        toast.error((err as Error).message || "Failed to add item manually");
      },
    });
  };

  const handleToggleTorch = useCallback(() => {
    setTorchOn(prev => !prev);
  }, []);

  return (
    <ScannerErrorBoundary>
      <div className="relative h-[100dvh] w-full overflow-hidden bg-black">
        <video
          ref={videoRef}
          playsInline
          muted
          autoPlay
          suppressHydrationWarning
          className="absolute inset-0 z-0 h-full w-full object-cover"
        />

        <TopBar
          currentFormat={activeFormat}
          setFormat={f => setActiveFormat(f as ScanFormat)}
          hasFlash={hasTorch}
          isFlashOn={torchOn}
          onToggleFlash={handleToggleTorch}
        />

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
            onExtractionFailure={handleExtractionFailure}
            onShowManualForm={handleShowManualForm}
            format={activeFormat}
            torchOn={torchOn}
            onTorchCapabilityFound={setHasTorch}
          />
        )}
        {result && (
          <SuccessCard
            isbn={result.isbn}
            meta={result.meta}
            onDismiss={handleDismiss}
            snappedCover={snappedCover}
            onShowManualForm={handleShowManualForm}
          />
        )}

        {candidates && (
          <DisambiguationSheet
            candidates={candidates.items}
            onSelect={choice => {
              setCandidates(null);
              // Derive a stable identifier from the selected candidate
              const selectedIdentifier =
                (typeof choice === "object" &&
                  choice !== null &&
                  "identifier" in choice &&
                  (choice.identifier as string)) ||
                (typeof choice === "object" && choice !== null && "barcode" in choice && (choice.barcode as string)) ||
                (typeof choice === "object" && choice !== null && "isbn" in choice && (choice.isbn as string)) ||
                candidates.isbn;

              setResult({ isbn: selectedIdentifier, meta: choice });
            }}
            onDismiss={handleDismiss}
          />
        )}

        {showManual && (
          <div className="absolute inset-x-0 bottom-0 z-40 bg-card rounded-t-3xl shadow-2xl pb-12 animate-[slide-up_0.3s_ease-out_forwards]">
            <ManualEntryForm
              onSubmit={handleManualSubmit}
              onCancel={() => setShowManual(false)}
              initialTitle={title}
              initialAuthors={author}
              initialFormat={activeFormat}
              initialIdentifier={initialIdentifier}
            />
          </div>
        )}
      </div>
    </ScannerErrorBoundary>
  );
}
