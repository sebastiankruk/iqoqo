"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Camera, Search } from "lucide-react";
import type { IsbnMeta } from "@/types/frbr";

const TABS = [
  { id: "barcode", label: "Barcode" },
  { id: "manual", label: "Manual Search" },
] as const;

type TabId = (typeof TABS)[number]["id"];

interface BottomSheetProps {
  onFound: (isbn: string, meta: IsbnMeta) => void;
}

/** Bottom-sheet panel with barcode scanner and manual ISBN entry. */
export function BottomSheet({ onFound }: BottomSheetProps) {
  const [activeTab, setActiveTab] = useState<TabId>("barcode");
  const [manualIsbn, setManualIsbn] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [scannerActive, setScannerActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scannerRef = useRef<{ clear: () => Promise<void> } | null>(null);
  const qrBoxId = "html5qr-code-full-region";

  /* ── Real barcode scanning via html5-qrcode ── */
  const startScanner = useCallback(async () => {
    setError(null);
    try {
      const { Html5Qrcode } = await import("html5-qrcode");
      const scanner = new Html5Qrcode(qrBoxId);

      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        async (decodedText) => {
          // decodedText is the raw barcode value (usually an ISBN)
          await scanner.stop();
          setScannerActive(false);
          await lookupIsbn(decodedText.replace(/[^0-9Xx]/g, ""));
        },
        () => { /* Frame scan failure – ignored */ }
      );

      scannerRef.current = { clear: () => scanner.stop() };
      setScannerActive(true);
    } catch (e) {
      setError((e as Error).message ?? "Camera unavailable");
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* Stop scanner when switching away from barcode tab */
  useEffect(() => {
    if (activeTab !== "barcode" && scannerRef.current) {
      scannerRef.current.clear().catch(() => {});
      scannerRef.current = null;
      setScannerActive(false);
    }
  }, [activeTab]);

  /* Cleanup on unmount */
  useEffect(() => {
    return () => {
      scannerRef.current?.clear().catch(() => {});
    };
  }, []);

  const lookupIsbn = async (isbn: string) => {
    if (!isbn) return;
    setIsSearching(true);
    setError(null);
    try {
      const { apiClient } = await import("@/lib/api/client");
      const res = await apiClient.get<IsbnMeta>(`/isbn/${isbn}`);
      onFound(isbn, res.data);
    } catch (e) {
      setError("Could not find this ISBN. Try entering it manually.");
    } finally {
      setIsSearching(false);
    }
  };

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
            {/* Hidden div used by html5-qrcode – positioned off-screen */}
            <div
              id={qrBoxId}
              className="absolute -left-[9999px] h-px w-px overflow-hidden"
            />

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
