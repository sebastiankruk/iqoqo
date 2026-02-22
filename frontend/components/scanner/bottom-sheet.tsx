"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Camera, Search } from "lucide-react";
import type { IsbnMeta } from "@/types/frbr";

const TABS = [
  { id: "barcode", label: "Barcode" },
  { id: "manual", label: "Manual Search" },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** Minimal type shim for BarcodeDetector (not yet in lib.dom.d.ts). */
interface BarcodeDetectorResult {
  rawValue: string;
}
interface BarcodeDetectorLike {
  detect(source: HTMLVideoElement): Promise<BarcodeDetectorResult[]>;
}
declare global {
  interface Window {
    BarcodeDetector?: new (options: { formats: string[] }) => BarcodeDetectorLike;
  }
}

interface BottomSheetProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onFound: (isbn: string, meta: IsbnMeta) => void;
}

/** Bottom-sheet panel with barcode scanner and manual ISBN entry. */
export function BottomSheet({ videoRef, onFound }: BottomSheetProps) {
  const [activeTab, setActiveTab] = useState<TabId>("barcode");
  const [manualIsbn, setManualIsbn] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [scannerActive, setScannerActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);

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
  }, [videoRef]);

  /* ── ISBN API lookup ── */
  const lookupIsbn = useCallback(
    async (isbn: string) => {
      if (!isbn) return;
      setIsSearching(true);
      setError(null);
      try {
        const { apiClient } = await import("@/lib/api/client");
        const res = await apiClient.get<IsbnMeta>(`/isbn/${isbn}`);
        onFound(isbn, res.data);
      } catch {
        setError("Could not find this ISBN. Try entering it manually.");
      } finally {
        setIsSearching(false);
      }
    },
    [onFound],
  );

  /* ── Start camera + BarcodeDetector scan loop ── */
  const startScanner = useCallback(async () => {
    setError(null);
    const video = videoRef.current;
    if (!video) return;

    try {
      /* getUserMedia – Safari requires { ideal } not { exact } for facingMode */
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
      /* play() on a React-owned element with playsInline+muted works in Safari */
      await video.play();
      setScannerActive(true);

      if (!window.BarcodeDetector) {
        setError("Barcode detection is not supported in this browser. Please use manual ISBN entry.");
        return;
      }

      const detector = new window.BarcodeDetector({
        /* ISBN barcodes are EAN-13; include UPC variants as fallback */
        formats: ["ean_13", "ean_8", "upc_a", "upc_e"],
      });

      const scan = async () => {
        if (!streamRef.current || !video) return;
        try {
          const barcodes = await detector.detect(video);
          if (barcodes.length > 0) {
            const raw = barcodes[0].rawValue;
            stopScanner();
            await lookupIsbn(raw.replace(/[^0-9Xx]/g, ""));
            return;
          }
        } catch {
          /* Frame not ready yet – keep looping */
        }
        rafRef.current = requestAnimationFrame(scan);
      };

      rafRef.current = requestAnimationFrame(scan);
    } catch (e) {
      setError((e as Error).message ?? "Camera unavailable");
      stopScanner();
    }
  }, [videoRef, lookupIsbn, stopScanner]);

  /* Stop scanner when switching away from barcode tab */
  useEffect(() => {
    if (activeTab !== "barcode") stopScanner();
  }, [activeTab, stopScanner]);

  /* Cleanup on unmount */
  useEffect(() => {
    return () => {
      stopScanner();
    };
  }, [stopScanner]);

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    lookupIsbn(manualIsbn.replace(/[^0-9Xx]/g, ""));
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
              onClick={() => setActiveTab(tab.id)}
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

        {activeTab === "manual" && (
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
        )}
      </div>
    </div>
  );
}
