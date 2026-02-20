"use client";

import { useState, useCallback } from "react";
import { TopBar } from "@/components/scanner/top-bar";
import { Viewfinder } from "@/components/scanner/viewfinder";
import { BottomSheet } from "@/components/scanner/bottom-sheet";
import { SuccessCard } from "@/components/scanner/success-card";
import type { IsbnMeta } from "@/types/frbr";

/**
 * Full-screen camera scanner page.
 * The html5-qrcode library handles the actual barcode detection; this page
 * manages the result state and transitions between the scanning UI and the
 * "Book Found" success card.
 */
export default function ScanPage() {
  const [result, setResult] = useState<{
    isbn: string;
    meta: IsbnMeta;
  } | null>(null);

  const handleFound = useCallback((isbn: string, meta: IsbnMeta) => {
    setResult({ isbn, meta });
  }, []);

  const handleDismiss = useCallback(() => {
    setResult(null);
  }, []);

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden bg-black">
      {/* Simulated camera feed background */}
      <div className="absolute inset-0" aria-hidden="true">
        <div className="h-full w-full bg-[#1a1a1e]">
          <div
            className="h-full w-full opacity-[0.07]"
            style={{
              backgroundImage:
                "radial-gradient(circle at 1px 1px, rgba(255,255,255,0.3) 1px, transparent 0)",
              backgroundSize: "24px 24px",
            }}
          />
        </div>
      </div>

      <TopBar />
      <Viewfinder />

      {!result && <BottomSheet onFound={handleFound} />}
      {result && (
        <SuccessCard
          isbn={result.isbn}
          meta={result.meta}
          onDismiss={handleDismiss}
        />
      )}
    </div>
  );
}
