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

import { useState } from "react";
import { Viewfinder } from "@/components/scanner/viewfinder";
import { SuccessCard } from "@/components/scanner/success-card";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { fetchWithAuth } from "@/lib/api/server-client";

/**
 * Full-screen camera scanner page.
 *
 * The <video> element is owned by React so that Safari honours playsInline
 * and does not abort the stream. The BottomSheet component receives a ref to
 * it and drives getUserMedia + BarcodeDetector scanning.
 */
interface ResultItem {
  title: string;
  message: string;
  item_id: number;
}
export default function ScanPage() {
  const [scanning, setScanning] = useState(true);
  const [result, setResult] = useState<ResultItem | null>(null);
  const router = useRouter();

  const handleDetected = async (barcode: string) => {
    setScanning(false);
    toast.loading("Resolving barcode...");

    try {
      const res = await fetchWithAuth("/api/scan", {
        method: "POST",
        body: JSON.stringify({ barcode })
      });

      const data = await res.json();

      if (res.ok) {
        toast.dismiss();
        toast.success("Added to library!");
        setResult(data);
      } else {
        toast.dismiss();
        toast.error(data.error || "Failed to scan item");
        setScanning(true); // resume scanning on fail
      }
    } catch (_err) {
      toast.dismiss();
      toast.error("Network error. Try again.");
      setScanning(true);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-black">
      {scanning ? (
        <Viewfinder onDetect={handleDetected} />
      ) : (
        <div className="flex-1 flex items-center justify-center p-4">
          {result && (
            <SuccessCard
              title={result.title}
              message={result.message}
              onViewItem={() => router.push(`/item/${result.item_id}`)}
              onScanNext={() => {
                setResult(null);
                setScanning(true);
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
