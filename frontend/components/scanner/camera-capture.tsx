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
 * Camera capture button.
 *
 * Operates in two modes depending on whether `manifestationId` is supplied:
 *
 * 1. **Cover upload** – posts the image to `/manifestations/:id/cover` and
 *    calls `onUploadComplete` on success.
 * 2. **Vision extraction** – posts the image to `/vision/extract` and calls
 *    `onExtractComplete` with the extracted `{ Title, Authors }` payload when
 *    the server returns `success: true`.
 *
 * @module components/scanner/camera-capture
 */
"use client";

import React, { useRef, useState } from "react";
import { Camera, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api/client";

/** API response envelope returned by backend endpoints. */
interface ApiEnvelope<T> {
  success: boolean;
  data: T | null;
  error?: string | null;
}

/** Extracted book metadata returned by the `/vision/extract` endpoint. */
interface ExtractedMetadata {
  Title?: string;
  Authors?: string[];
}

interface CameraCaptureProps {
  /** If set, the component uploads the image as a cover for this manifestation. */
  manifestationId?: number;
  /** Called after a successful cover upload (mode 1). */
  onUploadComplete?: () => void;
  /** Called with extracted metadata after a successful vision extraction (mode 2). */
  onExtractComplete?: (data: ExtractedMetadata) => void;
  className?: string;
}

/**
 * A camera/file-capture button that either uploads a cover image or triggers
 * vision-based metadata extraction, depending on the `manifestationId` prop.
 *
 * @param root0 - Component props.
 * @param root0.manifestationId - If set, uploads the image as a cover for this manifestation.
 * @param root0.onUploadComplete - Called after a successful cover upload (mode 1).
 * @param root0.onExtractComplete - Called with extracted metadata after vision extraction (mode 2).
 * @param root0.className - Optional CSS class name applied to the wrapper div.
 * @returns The rendered camera capture button element.
 */
export function CameraCapture({ manifestationId, onUploadComplete, onExtractComplete, className }: CameraCaptureProps) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCapture = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("cover", file);

    try {
      if (manifestationId) {
        // Mode 1: Upload a user-contributed cover for a known manifestation
        await apiClient.post(`/manifestations/${manifestationId}/cover`, formData);
        if (onUploadComplete) onUploadComplete();
      } else {
        // Mode 2: OCR / Vision Metadata Extraction
        const response = await apiClient.post<ApiEnvelope<ExtractedMetadata>>(`/vision/extract`, formData);
        const envelope = response.data;
        if (envelope.success && envelope.data) {
          if (onExtractComplete) onExtractComplete(envelope.data);
        } else {
          console.error("Vision extraction failed:", envelope.error ?? "Unknown error");
        }
      }
    } catch (error) {
      console.error("Failed to process cover image", error);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className={className}>
      <input
        type="file"
        accept="image/*"
        capture="environment"
        ref={fileInputRef}
        onChange={handleCapture}
        className="hidden"
      />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3"
      >
        {uploading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Processing...
          </>
        ) : (
          <>
            <Camera className="mr-2 h-4 w-4" />
            Snap Cover
          </>
        )}
      </button>
    </div>
  );
}
