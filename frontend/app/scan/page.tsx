"use client";

import { useState, useCallback, useRef } from "react";
import { TopBar } from "@/components/scanner/top-bar";
import { Viewfinder } from "@/components/scanner/viewfinder";
import { BottomSheet } from "@/components/scanner/bottom-sheet";
import { SuccessCard } from "@/components/scanner/success-card";
import type { IsbnMeta } from "@/types/frbr";

/**
 * Full-screen camera scanner page.
 *
 * The <video> element is owned by React so that Safari honours playsInline
 * and does not abort the stream. The BottomSheet component receives a ref to
 * it and drives getUserMedia + BarcodeDetector scanning.
 */
export default function ScanPage() {
  const [result, setResult] = useState<{
    isbn: string;
    meta: IsbnMeta;
  } | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  const handleFound = useCallback((isbn: string, meta: IsbnMeta) => {
    setResult({ isbn, meta });
  }, []);

  const handleDismiss = useCallback(() => {
    setResult(null);
  }, []);

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden bg-black">
      {/*
       * React-owned <video> so we control all attributes (playsInline, muted).
       * Safari requires playsInline to avoid aborting the stream, and muted
       * to satisfy autoplay policies.
       */}
      <video
        ref={videoRef}
        playsInline
        muted
        autoPlay
        aria-hidden="true"
        className="absolute inset-0 z-0 h-full w-full object-cover"
      />

      <TopBar />
      <Viewfinder />

      {!result && <BottomSheet videoRef={videoRef} onFound={handleFound} />}
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
