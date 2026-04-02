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

import { useState, useRef, useEffect, useCallback } from "react";
import { Camera, Search, ImagePlus } from "lucide-react";
import type { IsbnMeta } from "@/types/frbr";
import { CameraCapture } from "@/components/scanner/camera-capture";

const TABS = [
  { id: "barcode", label: "Barcode" },
  { id: "cover", label: "Snap Cover" },
  { id: "manual", label: "Manual Search" },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** Props for BottomSheet component */
interface BottomSheetProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onFound: (isbn: string, meta: IsbnMeta) => void;
  onScannerStateChange?: (isActive: boolean) => void;
  onTabChange?: (tabId: "barcode" | "cover" | "manual") => void;
  onExtractComplete?: (data: { Title?: string; Authors?: string[] }, file?: File) => void;
  onShowManualForm?: () => void;
  format?: "book" | "cd" | "vinyl";
}

/**
 * Bottom-sheet panel with barcode scanner and manual ISBN entry.
 *
 * @param root0 - The props object
 * @param root0.videoRef - The video element ref
 * @param root0.onFound - Callback when a barcode is found
 * @param root0.onScannerStateChange - Optional callback when scanner active state changes
 * @param root0.onTabChange - Optional callback when the bottom sheet tab changes
 * @param root0.onExtractComplete - Optional callback when cover metadata is extracted
 * @param root0.onShowManualForm - Optional callback to show manual entry form
 * @param root0.format - The current media format (book, cd, vinyl)
 * @returns {JSX.Element} The component
 */
export function BottomSheet({
  videoRef,
  onFound,
  onScannerStateChange,
  onTabChange,
  onExtractComplete,
  onShowManualForm,
  format = "book",
}: BottomSheetProps) {
  const [activeTab, setActiveTab] = useState<TabId>("barcode");

  const handleTabChange = useCallback(
    (tabId: TabId) => {
      setActiveTab(tabId);
      if (onTabChange) onTabChange(tabId);
    },
    [onTabChange]
  );
  const [manualIsbn, setManualIsbn] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [scannerActive, setScannerActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const [isUploadingCover, setIsUploadingCover] = useState(false);
  const barcodeEnabledRef = useRef<boolean>(true);

  // Sync ref with state
  useEffect(() => {
    barcodeEnabledRef.current = activeTab === "barcode";
  }, [activeTab]);

  /* ── Stop everything ── */
  const stopScanner = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    const video = videoRef.current;
    if (video) {
      video.srcObject = null;
    }
    setScannerActive(false);
    if (onScannerStateChange) onScannerStateChange(false);
  }, [videoRef, onScannerStateChange]);

  /* ── Barcode API lookup ── */
  const lookupBarcode = useCallback(
    async (rawBarcode: string) => {
      if (!rawBarcode) return;
      const barcode = rawBarcode.replace(/[^0-9Xx]/g, "").toUpperCase();
      // Allow 8, 10, 12, or 13 digit variations (EAN-8, ISBN-10, UPC-A, EAN-13)
      const isValidBarcode = /^\d{8,13}[\dX]?$/.test(barcode);

      if (!isValidBarcode) {
        setError("Please enter a valid barcode (8-13 characters).");
        return;
      }
      setIsSearching(true);
      setError(null);
      try {
        const { apiFetch } = await import("@/lib/api/client");
        // Using generic lookup instead of purely ISBN lookup
        const data = await apiFetch<IsbnMeta>(`/lookup/${barcode}`);
        onFound(barcode, data);
      } catch (e: unknown) {
        if (e && typeof e === "object" && "message" in e && typeof e.message === "string") {
          setError(e.message);
        } else {
          setError("Could not look up this barcode. Please try again.");
        }
      } finally {
        setIsSearching(false);
      }
    },
    [onFound]
  );

  /* ── Start camera + ZXing scan loop ── */
  const startScanner = useCallback(async () => {
    setError(null);
    const video = videoRef.current;
    if (!video) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });

      streamRef.current = stream;
      video.srcObject = stream;
      await video.play();
      setScannerActive(true);
      if (onScannerStateChange) onScannerStateChange(true);

      const { BrowserMultiFormatReader } = await import("@zxing/browser");
      const { BarcodeFormat, DecodeHintType } = await import("@zxing/library");

      const hints = new Map<number, unknown>();
      hints.set(DecodeHintType.POSSIBLE_FORMATS, [
        BarcodeFormat.EAN_13,
        BarcodeFormat.EAN_8,
        BarcodeFormat.UPC_A,
        BarcodeFormat.UPC_E,
      ]);

      const reader = new BrowserMultiFormatReader(hints);
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");

      const scan = () => {
        if (!streamRef.current || !video || !ctx) return;

        if (video.videoWidth > 0 && video.videoHeight > 0 && barcodeEnabledRef.current) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

          try {
            const result = reader.decodeFromCanvas(canvas);
            stopScanner();
            lookupBarcode(result.getText());
            return;
          } catch {
            /* Keep looping */
          }
        }

        rafRef.current = requestAnimationFrame(scan);
      };

      rafRef.current = requestAnimationFrame(scan);
    } catch (e) {
      setError((e as Error).message ?? "Camera unavailable");
      stopScanner();
    }
  }, [videoRef, lookupBarcode, stopScanner, onScannerStateChange]);

  useEffect(() => {
    if (activeTab === "manual") stopScanner();
  }, [activeTab, stopScanner]);

  /* Capture snapshot directly from live video feed */
  const handleSnapFromVideo = useCallback(async () => {
    const video = videoRef.current;
    if (!video || !streamRef.current) return;

    setIsUploadingCover(true);
    setError(null);
    try {
      const sourceWidth = video.videoWidth;
      const sourceHeight = video.videoHeight;

      // Calculate crop dimensions based on format
      let targetWidth = sourceWidth;
      let targetHeight = sourceHeight;
      const isAudio = format === "cd" || format === "vinyl";

      if (isAudio) {
        // 1:1 Aspect Ratio
        const size = Math.min(sourceWidth, sourceHeight);
        targetWidth = size;
        targetHeight = size;
      } else {
        // 2:3 Aspect Ratio (Book)
        const possibleHeightByWidth = (sourceWidth * 3) / 2;
        const possibleWidthByHeight = (sourceHeight * 2) / 3;

        if (possibleHeightByWidth <= sourceHeight) {
          targetWidth = sourceWidth;
          targetHeight = possibleHeightByWidth;
        } else {
          targetWidth = possibleWidthByHeight;
          targetHeight = sourceHeight;
        }
      }

      const startX = (sourceWidth - targetWidth) / 2;
      const startY = (sourceHeight - targetHeight) / 2;

      const canvas = document.createElement("canvas");
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not map camera feed");

      // Draw cropped area
      ctx.drawImage(video, startX, startY, targetWidth, targetHeight, 0, 0, targetWidth, targetHeight);
      
      const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, "image/jpeg", 0.9));
      if (!blob) throw new Error("Failed to encode image");

      const file = new File([blob], "cover_snapshot.jpg", { type: "image/jpeg" });
      const formData = new FormData();
      formData.append("cover", file);

      const { apiClient } = await import("@/lib/api/client");
      const response = await apiClient.post<{
        success: boolean;
        data: { Title?: string; Authors?: string[] } | null;
        error?: string | null;
      }>(`/vision/extract`, formData, { headers: { "Content-Type": "multipart/form-data" } });
      
      const envelope = response.data;
      if (envelope.success && envelope.data) {
        if (onExtractComplete) onExtractComplete(envelope.data, file);
      } else {
        setError(envelope.error ?? "Failed to extract metadata");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not snap cover");
    } finally {
      setIsUploadingCover(false);
    }
  }, [videoRef, onExtractComplete, format]);

  /* Cleanup on unmount */
  useEffect(() => {
    return () => { stopScanner(); };
  }, [stopScanner]);

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    lookupBarcode(manualIsbn);
  };

  return (
    <div className="absolute inset-x-0 bottom-0 z-20 flex h-[40%] flex-col rounded-t-3xl bg-card shadow-[0_-8px_40px_rgba(0,0,0,0.25)]">
      <div className="flex justify-center pt-3 pb-2"><div className="h-1 w-10 rounded-full bg-border" /></div>
      <div className="flex justify-center px-6">
        <div className="inline-flex rounded-xl bg-secondary p-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id as TabId)}
              className={`rounded-lg px-4 py-2 text-xs font-semibold transition-all ${
                activeTab === tab.id ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6">
        {error && <p className="text-center text-xs text-destructive">{error}</p>}

        {activeTab === "barcode" && (
          <>
            <button onClick={scannerActive ? undefined : startScanner} disabled={isSearching} className="group relative flex items-center justify-center">
              <span className="absolute h-[76px] w-[76px] rounded-full border-[3px] border-primary/30 animate-[pulse-ring_2s_ease-in-out_infinite]" />
              <span className="absolute h-[68px] w-[68px] rounded-full border-[3px] border-primary" />
              <span className="relative flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground transition-transform group-active:scale-90">
                <Camera className={`h-6 w-6 ${scannerActive ? "animate-pulse" : ""}`} />
              </span>
            </button>
            <p className="text-xs text-muted-foreground">{scannerActive ? "Scanning – point at barcode" : "Tap to start camera"}</p>
          </>
        )}

        {activeTab === "cover" && (
          <div className="flex w-full flex-col gap-4">
            {!scannerActive ? (
              <button onClick={startScanner} className="flex w-full items-center justify-center rounded-xl bg-primary py-3 font-semibold text-primary-foreground shadow-sm">
                <Camera className="mr-2 h-5 w-5" /> Start Live Camera
              </button>
            ) : (
              <button onClick={handleSnapFromVideo} disabled={isUploadingCover} className="flex w-full items-center justify-center rounded-xl bg-primary py-4 font-semibold text-primary-foreground shadow-md ring-2 ring-primary/20 ring-offset-2 disabled:opacity-50">
                {isUploadingCover ? <span className="animate-pulse">Analyzing frame...</span> : <><Camera className="mr-2 h-5 w-5" /> Snap Live Frame</>}
              </button>
            )}
            <div className="relative flex w-full items-center py-1">
              <div className="flex-grow border-t border-border"></div>
              <span className="mx-4 flex-shrink-0 text-xs text-muted-foreground uppercase tracking-widest">or</span>
              <div className="flex-grow border-t border-border"></div>
            </div>
            <CameraCapture capture={false} label="Upload from Gallery" icon={<ImagePlus className="mr-2 h-5 w-5" />} onExtractComplete={(data, file) => onExtractComplete?.(data, file)} className="flex w-full justify-center [&>button]:h-12 [&>button]:w-full [&>button]:rounded-xl [&>button]:border [&>button]:border-border [&>button]:bg-card [&>button]:font-semibold [&>button]:text-foreground [&>button]:hover:bg-accent" />
          </div>
        )}

        {activeTab === "manual" && (
          <div className="flex w-full flex-col">
            <form onSubmit={handleManualSearch} className="w-full">
              <div className="relative">
                <input type="text" value={manualIsbn} onChange={e => setManualIsbn(e.target.value)} placeholder="Enter barcode or title..." className="h-11 w-full rounded-xl border border-border bg-secondary px-4 pr-10 text-sm text-foreground outline-none focus:border-primary focus:ring-2" />
                <button type="submit" disabled={isSearching || !manualIsbn} className="absolute inset-y-0 right-3 flex items-center text-muted-foreground hover:text-foreground">
                  <Search className="h-4 w-4" />
                </button>
              </div>
              <p className="mt-2 text-center text-xs text-muted-foreground">{isSearching ? "Looking up…" : "Try ISBN or UPC"}</p>
            </form>
            <div className="mt-5 flex flex-col items-center border-t border-border pt-4">
              <button type="button" onClick={onShowManualForm} className="w-full rounded-xl bg-secondary px-4 py-3 text-sm font-semibold shadow-sm hover:bg-secondary/80">
                Manual Entry Form
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
