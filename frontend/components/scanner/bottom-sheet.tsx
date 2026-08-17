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
import { ScanFormat } from "@/types/taxonomy";
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
  onExtractionFailure?: (ean: string) => void;
  onShowManualForm?: (isbn?: string) => void;
  format?: ScanFormat;
  torchOn?: boolean;
  onTorchCapabilityFound?: (hasTorch: boolean) => void;
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
 * @param root0.onExtractionFailure - Optional callback when extraction fails
 * @param root0.onShowManualForm - Optional callback to show manual entry form
 * @param root0.format - The current media format (book, cd, vinyl)
 * @param root0.torchOn - Whether the flashlight should be on
 * @param root0.onTorchCapabilityFound - Callback when flashlight capability is detected
 * @returns {JSX.Element} The component
 */
export function BottomSheet({
  videoRef,
  onFound,
  onScannerStateChange,
  onTabChange,
  onExtractComplete,
  onExtractionFailure,
  onShowManualForm,
  format = "book",
  torchOn = false,
  onTorchCapabilityFound,
}: BottomSheetProps) {
  const [activeTab, setActiveTab] = useState<TabId>("barcode");

  const formatToApiParam = (fmt?: string): string => {
    if (fmt === "movie" || fmt === "video") return "movie";
    if (fmt === "board_game" || fmt === "boardgame") return "board_game";
    if (fmt === "puzzle") return "puzzle";
    if (fmt === "music" || fmt === "audio") return "music";
    if (fmt === "book") return "book";
    return "";
  };

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
  const [lastSearchedBarcode, setLastSearchedBarcode] = useState<string>("");
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
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
    if (onTorchCapabilityFound) onTorchCapabilityFound(false);
  }, [videoRef, onScannerStateChange, onTorchCapabilityFound]);

  /** Apply Torch (Flashlight) constraints when the [torchOn] state changes. */
  useEffect(() => {
    /** Internal function to apply media constraints to the active tracks. */
    async function applyTorch() {
      if (!streamRef.current) return;
      const track = streamRef.current.getVideoTracks()[0];
      if (track) {
        try {
          // Just apply the constraint. Some Android devices hide the torch capability
          // or report it as undefined, but still accept the constraint if applied.
          await track.applyConstraints({
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            advanced: [{ torch: torchOn }] as any,
          });
        } catch (err) {
          console.error("Failed to apply torch constraints", err);
        }
      }
    }
    applyTorch();
  }, [torchOn]);

  /* ── Barcode API lookup ── */
  const lookupBarcode = useCallback(
    async (rawBarcode: string, isManualText: boolean = false) => {
      if (!rawBarcode) return;

      let query = rawBarcode.trim();

      if (!isManualText) {
        query = query.replace(/[^0-9Xx]/g, "").toUpperCase();
        // Allow 8, 10, 12, or 13 digit variations (EAN-8, ISBN-10, UPC-A, EAN-13)
        const isValidBarcode = /^\d{8,13}[\dX]?$/.test(query);

        if (!isValidBarcode) {
          setError("Please enter a valid barcode (8-13 characters).");
          return;
        }
      } else {
        // If it looks like a user typed a barcode, clean it up but don't strictly reject other text
        const digitsOnly = query.replace(/[^0-9Xx]/g, "").toUpperCase();
        if (/^\d{8,13}[\dX]?$/.test(digitsOnly)) {
          query = digitsOnly;
        }
      }

      setLastSearchedBarcode(query);
      setIsSearching(true);
      setError(null);
      try {
        const { apiFetch } = await import("@/lib/api/client");
        const formatParam = formatToApiParam(format);
        const encodedQuery = encodeURIComponent(query);
        const url = formatParam ? `/lookup/${encodedQuery}?format=${formatParam}` : `/lookup/${encodedQuery}`;

        let timeoutId: ReturnType<typeof setTimeout> | undefined;
        const timeoutPromise = new Promise<never>((_, reject) => {
          timeoutId = setTimeout(() => reject(new Error("Lookup timed out. Switching to manual entry.")), 10000);
        });

        const data = await Promise.race([apiFetch<IsbnMeta>(url), timeoutPromise]).finally(() => {
          if (timeoutId) clearTimeout(timeoutId);
        });

        onFound(query, data);
      } catch (e: unknown) {
        const errorMessage =
          e && typeof e === "object" && "message" in e && typeof e.message === "string"
            ? e.message
            : "Could not look up this item. Please try again.";
        setError(errorMessage);
        if (onShowManualForm) {
          onShowManualForm(query);
        }
      } finally {
        setIsSearching(false);
      }
    },
    [onFound, format, onShowManualForm]
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

      const track = stream.getVideoTracks()[0];
      if (track && onTorchCapabilityFound) {
        // Detect torch support by attempting to apply a no-op constraint.
        // We wait a brief moment for Android devices hardware to warm up.
        setTimeout(() => {
          try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const capabilities = (track.getCapabilities?.() as any) || {};
            if (capabilities.torch !== undefined) {
              onTorchCapabilityFound(true);
            } else {
              onTorchCapabilityFound(false);
            }
          } catch {
            onTorchCapabilityFound(false);
          }
        }, 500);
      }

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
  }, [videoRef, lookupBarcode, stopScanner, onScannerStateChange, onTorchCapabilityFound]);

  useEffect(() => {
    if (activeTab === "manual") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      stopScanner();
    }
  }, [activeTab, stopScanner]);

  /* Cleanup on unmount */
  useEffect(() => {
    return () => {
      stopScanner();
    };
  }, [stopScanner]);

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    lookupBarcode(manualIsbn.trim(), true);
  };

  return (
    <div className="absolute inset-x-0 bottom-0 z-20 flex h-[40%] flex-col rounded-t-3xl bg-card shadow-[0_-8px_40px_rgba(0,0,0,0.25)]">
      <div className="flex justify-center pt-3 pb-2">
        <div className="h-1 w-10 rounded-full bg-border" />
      </div>
      <div className="flex justify-center px-6">
        <div className="inline-flex rounded-xl bg-secondary p-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              data-testid={`scanner-tab-${tab.id}`}
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

      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 relative">
        {isSearching && (
          <div
            data-testid="scanner-searching-overlay"
            className="absolute inset-0 z-30 flex flex-col items-center justify-center rounded-t-2xl bg-background/90 backdrop-blur-sm p-6 text-center"
          >
            <div className="relative flex items-center justify-center mb-4">
              <div className="absolute h-14 w-14 rounded-full border-4 border-primary/30 border-t-transparent animate-[spin_1.5s_linear_infinite]" />
              <div className="h-10 w-10 rounded-full border-4 border-primary border-b-transparent animate-[spin_1s_linear_infinite_reverse]" />
            </div>
            <p className="animate-pulse text-sm font-semibold text-foreground">Searching catalog...</p>
            <p className="text-xs text-muted-foreground mt-1 mb-4">Looking up barcode {lastSearchedBarcode}</p>
            <button
              type="button"
              data-testid="scanner-skip-manual-button"
              onClick={() => onShowManualForm?.(lastSearchedBarcode)}
              className="text-xs text-muted-foreground underline hover:text-foreground transition-colors cursor-pointer"
            >
              Skip and enter manually
            </button>
          </div>
        )}

        {error && (
          <div className="flex w-full flex-col gap-3">
            <p className="text-center text-xs text-destructive">{error}</p>
            <button
              type="button"
              onClick={() => onShowManualForm?.(lastSearchedBarcode)}
              className="w-full rounded-xl bg-secondary px-4 py-2 text-sm font-semibold shadow-sm hover:bg-secondary/80"
            >
              Enter Manually
            </button>
          </div>
        )}

        {activeTab === "barcode" && (
          <div className="flex w-full flex-col items-center gap-4">
            <div className="relative flex w-full items-center justify-center">
              <button
                data-testid="start-camera-button"
                aria-label="Start camera"
                onClick={scannerActive ? undefined : startScanner}
                disabled={isSearching}
                className="group relative flex items-center justify-center"
              >
                <span className="absolute h-[76px] w-[76px] rounded-full border-[3px] border-primary/30 animate-[pulse-ring_2s_ease-in-out_infinite]" />
                <span className="absolute h-[68px] w-[68px] rounded-full border-[3px] border-primary" />
                <span className="relative flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground transition-transform group-active:scale-90">
                  <Camera className={`h-6 w-6 ${scannerActive ? "animate-pulse" : ""}`} />
                </span>
              </button>
            </div>
            <p className="text-xs text-muted-foreground">
              {scannerActive ? "Scanning – point at barcode" : "Tap to start camera"}
            </p>
          </div>
        )}

        {activeTab === "cover" && (
          <div className="flex w-full flex-col gap-3">
            {/* Primary action: camera (opens native picker on mobile) */}
            <CameraCapture
              capture="environment"
              label="Snap Cover"
              icon={<Camera className="mr-2 h-5 w-5" />}
              onExtractComplete={(data, file) => onExtractComplete?.(data, file)}
              onExtractionFailure={() => onExtractionFailure?.(lastSearchedBarcode)}
              format={format}
              className="flex w-full justify-center [&>div]:w-full [&>button]:h-14 [&>button]:w-full [&>button]:rounded-xl [&>button]:bg-primary [&>button]:font-semibold [&>button]:text-primary-foreground [&>button]:shadow-md [&>button]:ring-2 [&>button]:ring-primary/20 [&>button]:ring-offset-2 [&>button]:transition-all [&>button]:disabled:opacity-80"
            />

            {/* Secondary: gallery-only upload */}
            <CameraCapture
              capture={false}
              label="Upload from Gallery"
              icon={<ImagePlus className="mr-2 h-4 w-4" />}
              onExtractComplete={(data, file) => onExtractComplete?.(data, file)}
              onExtractionFailure={() => onExtractionFailure?.(lastSearchedBarcode)}
              format={format}
              className="flex w-full justify-center [&>button]:h-10 [&>button]:w-full [&>button]:rounded-xl [&>button]:border [&>button]:border-border [&>button]:bg-card [&>button]:text-sm [&>button]:font-semibold [&>button]:text-foreground [&>button]:hover:bg-accent"
            />

            {/* Error is already handled at the top */}
          </div>
        )}

        {activeTab === "manual" && (
          <div className="flex w-full flex-col">
            <form onSubmit={handleManualSearch} className="w-full">
              <div className="relative">
                <input
                  type="text"
                  value={manualIsbn}
                  onChange={e => setManualIsbn(e.target.value)}
                  placeholder="ISBN, UPC, Discogs ID, or Artist – Title…"
                  className="h-11 w-full rounded-xl border border-border bg-secondary px-4 pr-10 text-sm text-foreground outline-none focus:border-primary focus:ring-2"
                />
                <button
                  type="submit"
                  disabled={isSearching || !manualIsbn}
                  className="absolute inset-y-0 right-3 flex items-center text-muted-foreground hover:text-foreground"
                >
                  <Search className="h-4 w-4" />
                </button>
              </div>
            </form>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              {isSearching ? "Looking up…" : "Enter barcode, Discogs Release ID, or Artist – Title"}
            </p>
            <div className="mt-5 flex flex-col items-center border-t border-border pt-4">
              <button
                type="button"
                onClick={() => onShowManualForm?.(manualIsbn || lastSearchedBarcode)}
                className="w-full rounded-xl bg-secondary px-4 py-3 text-sm font-semibold shadow-sm hover:bg-secondary/80"
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
