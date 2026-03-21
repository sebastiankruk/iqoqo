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
  onExtractComplete?: (data: { Title?: string; Authors?: string[] }) => void;
  onShowManualForm?: () => void;
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
 * @returns {JSX.Element} The component
 */
export function BottomSheet({ videoRef, onFound, onScannerStateChange, onTabChange, onExtractComplete, onShowManualForm }: BottomSheetProps) {
  const [activeTab, setActiveTab] = useState<TabId>("barcode");

  const handleTabChange = useCallback((tabId: TabId) => {
    setActiveTab(tabId);
    if (onTabChange) onTabChange(tabId);
  }, [onTabChange]);
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
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    const video = videoRef.current;
    if (video) {
      video.srcObject = null;
    }
    setScannerActive(false);
    if (onScannerStateChange) onScannerStateChange(false);
  }, [videoRef, onScannerStateChange]);

  /* ── ISBN API lookup ── */
  const lookupIsbn = useCallback(
    /**
     * Looks up ISBN metadata and calls the onFound callback.
     *
     * @param {string} rawIsbn - Raw ISBN input (may contain hyphens/spaces).
     * @returns {Promise<void>} Resolves when lookup completes.
     */
    async (rawIsbn: string) => {
      if (!rawIsbn) return;
      const isbn = rawIsbn.replace(/[^0-9Xx]/g, "").toUpperCase();
      const isValidIsbn = /^\d{9}[\dX]$/.test(isbn) || /^\d{13}$/.test(isbn);

      if (!isValidIsbn) {
        setError("Please enter a valid ISBN-10 or ISBN-13.");
        return;
      }
      setIsSearching(true);
      setError(null);
      try {
        const { apiClient } = await import("@/lib/api/client");
        const res = await apiClient.get<IsbnMeta>(`/isbn/${isbn}`);
        onFound(isbn, res.data);
      } catch (e: unknown) {
        if (e && typeof e === "object" && "message" in e && typeof e.message === "string") {
          setError(e.message);
        } else {
          setError("Could not look up this ISBN. Please try again.");
        }
      } finally {
        setIsSearching(false);
      }
    },
    [onFound],
  );

  /* ── Start camera + ZXing scan loop (works in Safari, Firefox, Chrome) ── */
  /**
   * Starts the camera and initiates the barcode scanning process.
   */
  const startScanner = useCallback(async () => {
    setError(null);
    const video = videoRef.current;
    if (!video) return;

    try {
      /* getUserMedia – { ideal } not { exact } so desktop Safari doesn't reject */
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      video.srcObject = stream;
      /* playsInline + muted on the <video> element (set in page.tsx) satisfies Safari autoplay */
      await video.play();
      setScannerActive(true);
      if (onScannerStateChange) onScannerStateChange(true);

      /* Lazy-load ZXing – pure JS, works in all browsers */
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
            lookupIsbn(result.getText());
            return;
          } catch {
            /* NotFoundException – no barcode in this frame, keep looping */
          }
        }

        rafRef.current = requestAnimationFrame(scan);
      };

      rafRef.current = requestAnimationFrame(scan);
    } catch (e) {
      setError((e as Error).message ?? "Camera unavailable");
      stopScanner();
    }
  }, [videoRef, lookupIsbn, stopScanner, onScannerStateChange]);

  /* Stop scanner only if manual mode is entered */
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
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Could not map camera feed");

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
      if (!blob) throw new Error("Failed to encode image");

      const file = new File([blob], "cover_snapshot.jpg", { type: "image/jpeg" });
      const formData = new FormData();
      formData.append("cover", file);

      const { apiClient } = await import("@/lib/api/client");
      const response = await apiClient.post<{ success: boolean; data: { Title?: string; Authors?: string[] } | null; error?: string | null }>(`/vision/extract`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      const envelope = response.data;
      
      if (envelope.success && envelope.data) {
        if (onExtractComplete) onExtractComplete(envelope.data);
      } else {
        setError(envelope.error ?? "Failed to extract metadata");
      }
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
      else setError("Could not snap cover");
    } finally {
      setIsUploadingCover(false);
    }
  }, [videoRef, onExtractComplete]);

  /* Cleanup on unmount */
  useEffect(() => {
    return () => {
      stopScanner();
    };
  }, [stopScanner]);

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    lookupIsbn(manualIsbn);
  };

  return (
    <div className="absolute inset-x-0 bottom-0 z-20 flex h-[40%] flex-col rounded-t-3xl bg-card shadow-[0_-8px_40px_rgba(0,0,0,0.25)]">
      {/* Drag handle */}
      <div className="flex justify-center pt-3 pb-2">
        <div className="h-1 w-10 rounded-full bg-border" />
      </div>

      {/* Tabs */}
      <div className="flex justify-center px-6">
        <div className="inline-flex rounded-xl bg-secondary p-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id as TabId)}
              className={`rounded-lg px-4 py-2 text-xs font-semibold transition-all ${
                activeTab === tab.id
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6">
        {error && (
          <p className="text-center text-xs text-destructive">{error}</p>
        )}

        {activeTab === "barcode" && (
          <>
            {/* Capture button */}
            <button
              onClick={scannerActive ? undefined : startScanner}
              disabled={isSearching}
              className="group relative flex items-center justify-center"
              aria-label={scannerActive ? "Scanning…" : "Start camera"}
            >
              <span className="absolute h-[76px] w-[76px] rounded-full border-[3px] border-primary/30 animate-[pulse-ring_2s_ease-in-out_infinite]" />
              <span className="absolute h-[68px] w-[68px] rounded-full border-[3px] border-primary" />
              <span className="relative flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground transition-transform group-active:scale-90">
                <Camera className={`h-6 w-6 ${scannerActive ? "animate-pulse" : ""}`} />
              </span>
            </button>

            <p className="text-xs text-muted-foreground">
              {scannerActive
                ? "Scanning – point at barcode"
                : "Tap to start camera"}
            </p>
          </>
        )}

        {activeTab === "cover" && (
          <div className="flex w-full flex-col gap-4">
            {!scannerActive ? (
              <button
                onClick={startScanner}
                className="flex w-full items-center justify-center rounded-xl bg-primary py-3 font-semibold text-primary-foreground hover:bg-primary/90 shadow-sm"
              >
                <Camera className="mr-2 h-5 w-5" /> Start Live Camera
              </button>
            ) : (
              <button
                onClick={handleSnapFromVideo}
                disabled={isUploadingCover}
                className="flex w-full items-center justify-center rounded-xl bg-primary py-4 font-semibold text-primary-foreground hover:bg-primary/90 shadow-md ring-2 ring-primary/20 ring-offset-2 disabled:opacity-50"
              >
                {isUploadingCover ? (
                  <span className="animate-pulse">Analyzing frame...</span>
                ) : (
                  <>
                    <Camera className="mr-2 h-5 w-5" /> Snap Live Frame
                  </>
                )}
              </button>
            )}

            <div className="relative flex w-full items-center py-1">
              <div className="flex-grow border-t border-border"></div>
              <span className="mx-4 flex-shrink-0 text-xs text-muted-foreground uppercase tracking-widest">or</span>
              <div className="flex-grow border-t border-border"></div>
            </div>

            <CameraCapture
              capture={false}
              label="Upload from Gallery"
              icon={<ImagePlus className="mr-2 h-5 w-5" />}
              onExtractComplete={onExtractComplete}
              className="flex w-full justify-center [&>button]:h-12 [&>button]:w-full [&>button]:rounded-xl [&>button]:border [&>button]:border-border [&>button]:bg-card [&>button]:font-semibold [&>button]:text-foreground [&>button]:hover:bg-accent"
            />
            <p className="px-2 pt-2 text-center text-[0.7rem] text-muted-foreground leading-tight">
              Snap a frame from the live video feed or upload an existing image.
            </p>
          </div>
        )}

        {activeTab === "manual" && (
          <div className="flex w-full flex-col">
            <form onSubmit={handleManualSearch} className="w-full">
            <div className="relative">
              <input
                type="text"
                value={manualIsbn}
                onChange={(e) => setManualIsbn(e.target.value)}
                placeholder="Enter ISBN or title..."
                className="h-11 w-full rounded-xl border border-border bg-secondary px-4 pr-10 text-sm text-foreground placeholder-muted-foreground outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <button
                type="submit"
                disabled={isSearching || !manualIsbn}
                className="absolute inset-y-0 right-3 flex items-center text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
              >
                <Search className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              {isSearching ? "Looking up…" : "Try ISBN: 978-0-553-38016-8"}
            </p>
            </form>
            
            <div className="mt-5 flex flex-col items-center border-t border-border pt-4">
              <span className="mb-3 text-xs text-muted-foreground">Or enter full metadata manually</span>
              <button
                type="button"
                onClick={onShowManualForm}
                className="w-full rounded-xl bg-secondary px-4 py-3 text-sm font-semibold text-secondary-foreground shadow-sm hover:bg-secondary/80 transition-colors"
                aria-label="Enter details manually"
              >
                Manual Entry Form
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
