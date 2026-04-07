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
 * calls `onUploadComplete` on success.
 * 2. **Vision extraction** – posts the image to `/vision/extract` and calls
 * `onExtractComplete` with the extracted `{ Title, Authors }` payload when
 * the server returns `success: true`.
 *
 * @module components/scanner/camera-capture
 */
"use client";

import React, { useRef, useState, useEffect } from "react";
import { Camera, Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

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

/** Supported media formats for the scanner. */
export type MediaFormat = "book" | "cd" | "vinyl" | "audio" | "video" | "boardgame" | "puzzle";

interface CameraCaptureProps {
  /** If set, the component uploads the image as a cover for this manifestation. */
  manifestation_id?: number;
  /** Called after a successful cover upload (mode 1). */
  onUploadComplete?: () => void;
  /** Called with extracted metadata after vision extraction (mode 2). */
  onExtractComplete?: (data: ExtractedMetadata, file: File, format: MediaFormat) => void;
  className?: string;
  /** Label for the button */
  label?: string;
  /** Whether to force the camera (environment) or omit for gallery. */
  capture?: "environment" | "user" | false;
  /** Optional icon to replace the default Camera icon */
  icon?: React.ReactNode;
  /** If set, shows a confirmation dialog before opening the camera */
  confirmTitle?: string;
  /** Confirmation message */
  confirmMessage?: string;
  /** Initial media format */
  format?: MediaFormat;
}

/**
 * A camera/file-capture button that either uploads a cover image or triggers
 * vision-based metadata extraction, depending on the `manifestation_id` prop.
 *
 * @param props - Component props.
 * @param props.manifestation_id - If set, uploads the image as a cover for this manifestation.
 * @param props.onUploadComplete - Called after a successful cover upload (mode 1).
 * @param props.onExtractComplete - Called with extracted metadata after vision extraction (mode 2).
 * @param props.className - Optional CSS class name applied to the wrapper div.
 * @param props.capture - Whether to force the camera or omit for gallery
 * @param props.label - Label for the button
 * @param props.icon - Optional icon component
 * @param props.confirmTitle - If set, shows a confirmation dialog before opening the camera
 * @param props.confirmMessage - Confirmation message
 * @param props.format - Initial media format
 * @returns The rendered camera capture button element.
 */
export function CameraCapture({
  manifestation_id,
  onUploadComplete,
  onExtractComplete,
  className,
  capture = "environment",
  label = "Snap Cover",
  icon,
  confirmTitle,
  confirmMessage,
  format = "book",
}: CameraCaptureProps) {
  const [uploading, setUploading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [hasCamera, setHasCamera] = useState<boolean | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check if a physical camera is available
  useEffect(() => {
    let mounted = true;
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
      navigator.mediaDevices
        .enumerateDevices()
        .then(devices => {
          const videoInputs = devices.filter(d => d.kind === "videoinput");
          if (mounted) setHasCamera(videoInputs.length > 0);
        })
        .catch(() => {
          if (mounted) setHasCamera(false);
        });
    } else {
      setHasCamera(false);
    }
    return () => {
      mounted = false;
    };
  }, []);

  const startPolling = async (taskId: string) => {
    const maxRetries = 30; // 30 retries * 2s = 60s max
    const { apiClient: pollClient } = await import("@/lib/api/client");

    for (let i = 0; i < maxRetries; i++) {
      try {
        const response = await pollClient.get<ApiEnvelope<ExtractedMetadata | { status: string }>>(
          `/vision/extract/${taskId}`
        );
        const env = response.data;

        if (env.success && env.data) {
          // Check if data is the result (has Title) or just status
          if ("Title" in env.data) {
            return env.data;
          }
          const data = env.data as { status: string };
          if (data.status === "failed") {
            throw new Error(env.error || "Vision extraction failed");
          }
        }
      } catch (err) {
        if (err instanceof Error && err.message.includes("Vision extraction failed")) {
          throw err;
        }
        // Other network errors - just retry
      }

      // Wait 2 seconds before next poll
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
    throw new Error("Task timed out. Please try again or enter manually.");
  };

  const processFile = async (file: File) => {
    setUploading(true);
    const formData = new FormData();
    formData.append("cover", file);
    formData.append("format", format);

    try {
      if (manifestation_id) {
        // Mode 1: Upload a user-contributed cover for a known manifestation
        await apiClient.post(`/manifestations/${manifestation_id}/cover`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        if (onUploadComplete) onUploadComplete();
      } else {
        // Mode 2: OCR / Vision Metadata Extraction (Asynchronous)
        const response = await apiClient.post<ApiEnvelope<{ task_id: string }>>(`/vision/extract`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        const envelope = response.data;
        if (envelope.success && envelope.data?.task_id) {
          // Transition to polling
          const result = await startPolling(envelope.data.task_id);
          if (onExtractComplete) onExtractComplete(result, file, format);
        } else {
          toast.error(envelope.error ?? "Vision extraction submission failed");
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to process cover image";
      toast.error(message);
      console.error("Failed to process cover image", error);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleCapture = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      processFile(file);
    } else {
      toast.error("Please drop a valid image file.");
    }
  };

  const handleClick = () => {
    if (confirmTitle && confirmMessage) {
      setConfirmOpen(true);
    } else {
      fileInputRef.current?.click();
    }
  };

  const handleConfirmAction = () => {
    setConfirmOpen(false);
    fileInputRef.current?.click();
  };

  // Determine if we should show the drag & drop standard layout (desktop / no camera)
  const isDesktopMode = hasCamera === false || capture === false;

  return (
    <div
      className={`w-full ${className ?? ""} ${
        isDesktopMode
          ? "border-2 border-dashed border-border rounded-xl p-6 transition-colors " +
            (isDragging ? "bg-accent/50 border-primary" : "hover:bg-secondary/50")
          : isDragging
            ? "ring-2 ring-primary ring-offset-2 rounded-md"
            : ""
      }`}
      onDragOver={e => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept="image/*"
        {...(capture !== false && hasCamera !== false ? { capture } : {})}
        ref={fileInputRef}
        onChange={handleCapture}
        className="hidden"
      />

      {isDesktopMode ? (
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <UploadCloud
            className={`h-10 w-10 ${isDragging ? "text-primary animate-bounce" : "text-muted-foreground"}`}
          />
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium">Drag & Drop cover image here</p>
            <p className="text-xs text-muted-foreground">or click to browse files</p>
          </div>
          <Button onClick={handleClick} disabled={uploading} className="mt-2">
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing...
              </>
            ) : (
              "Browse Files"
            )}
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-4 w-full">
          <Button onClick={handleClick} disabled={uploading} variant="outline" className="w-full">
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                {icon || <Camera className="mr-2 h-4 w-4" />}
                {label}
              </>
            )}
          </Button>
        </div>
      )}

      {confirmTitle && (
        <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>{confirmTitle}</AlertDialogTitle>
              <AlertDialogDescription>{confirmMessage}</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleConfirmAction}>Continue</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  );
}
