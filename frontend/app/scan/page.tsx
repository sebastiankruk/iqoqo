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
