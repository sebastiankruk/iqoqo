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
 * 3. **Gallery upload** – posts the image to `/manifestations/:id/images` and
 * calls `onGalleryUploadComplete` on success.
 *
 * @module components/scanner/camera-capture
 */
"use client";

import React, { useRef, useState, useEffect } from "react";
import { Camera, Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { apiClient } from "@/lib/api/client";
import { Button, ButtonVariant } from "@/components/ui/button";
import { MediaFormat } from "@/types/frbr";
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

interface CameraCaptureProps {
  /** If set, the component uploads the image as a cover for this manifestation. */
  manifestation_id?: number;
  /** If true, the component uploads the image to the gallery (/images) instead of cover. */
  mode?: "cover" | "gallery" | "vision";
  /** The label for the gallery scan (front, back, disc, etc.). Used only in gallery mode. */
  galleryLabel?: string;
  /** Called after a successful cover upload (mode 1). */
  onUploadComplete?: () => void;
  /** Called after a successful gallery upload (mode 3). */
  onGalleryUploadComplete?: () => void;
  /** Called with extracted metadata after vision extraction (mode 2). */
  onExtractComplete?: (data: ExtractedMetadata, file: File, format: MediaFormat | string) => void;
  /** Called when vision extraction or polling fails. */
  onExtractionFailure?: () => void;
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
  format?: MediaFormat | string;
  /** Button variant */
  variant?: ButtonVariant;
  /** Optional CSS class name applied directly to the button */
  buttonClassName?: string;
  /** If true, forces the simplified button layout and applies to button */
  inline?: boolean;
  /** Source identifier for the scan (e.g. scanner_camera, user_upload) */
  source?: string;
}

/**
 * A camera/file-capture button that either uploads a cover image or triggers
 * vision-based metadata extraction, depending on the `manifestation_id` prop.
 *
 * @param props - Component props.
 * @param props.manifestation_id - If set, uploads the image as a cover for this manifestation.
 * @param props.mode - The upload mode: "cover", "gallery", or "vision".
 * @param props.galleryLabel - The label for the gallery scan (only for gallery mode).
 * @param props.onUploadComplete - Called after a successful cover upload (mode 1).
 * @param props.onGalleryUploadComplete - Called after a successful gallery upload (mode 3).
 * @param props.onExtractComplete - Called with extracted metadata after vision extraction (mode 2).
 * @param props.onExtractionFailure - Called when extraction or polling fails.
 * @param props.className - Optional CSS class name applied to the wrapper div.
 * @param props.capture - Whether to force the camera or omit for gallery.
 * @param props.label - Label for the button.
 * @param props.icon - Optional icon component.
 * @param props.confirmTitle - If set, shows a confirmation dialog before opening the camera.
 * @param props.confirmMessage - Confirmation message.
 * @param props.format - Initial media format.
 * @param props.variant - Button variant.
 * @param props.buttonClassName - Optional CSS class name applied directly to the button.
 * @param props.inline - If true, forces the simplified button layout and applies to button.
 * @param props.source - Source identifier for the scan (e.g. scanner_camera, user_upload).
 * @returns The rendered camera capture button element.
 */
export function CameraCapture({
  manifestation_id,
  mode = "cover",
  galleryLabel,
  onUploadComplete,
  onGalleryUploadComplete,
  onExtractComplete,
  onExtractionFailure,
  className,
  capture = "environment",
  label,
  icon,
  confirmTitle,
  confirmMessage,
  format = "book",
  variant,
  buttonClassName,
  inline,
  source,
}: CameraCaptureProps) {
  const t = useTranslations("scanner");
  const [uploading, setUploading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [hasCamera, setHasCamera] = useState<boolean | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check if a physical camera is available
  useEffect(() => {
    const controller = new AbortController();

    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
      navigator.mediaDevices
        .enumerateDevices()
        .then(devices => {
          if (controller.signal.aborted) return;
          const videoInputs = devices.filter(d => d.kind === "videoinput");
          setHasCamera(videoInputs.length > 0);
        })
        .catch(() => {
          if (controller.signal.aborted) return;
          setHasCamera(false);
        });
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setHasCamera(false);
    }
    return () => {
      controller.abort();
    };
  }, []);

  const startPolling = async (taskId: string) => {
    const maxRetries = 15; // 15 retries * 1s = 15s max timeout
    const { apiClient: pollClient } = await import("@/lib/api/client");

    for (let i = 0; i < maxRetries; i++) {
      try {
        const response = await pollClient.get<ApiEnvelope<ExtractedMetadata | { status: string }>>(
          `/vision/extract/${taskId}`,
          {
            signal:
              typeof AbortSignal !== "undefined" && "timeout" in AbortSignal ? AbortSignal.timeout(5000) : undefined,
          }
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
        // Detect terminal errors (500, 503) vs transient network errors
        const errorMessage = err instanceof Error ? err.message : "";
        const isServerError = errorMessage.includes("500") || errorMessage.includes("503");
        const isVisionFailed = errorMessage.includes("Vision extraction failed");

        // Re-throw immediately for server errors or vision failures
        if (isServerError || isVisionFailed) {
          throw err;
        }
        // For transient network errors, continue retrying
      }

      // Wait 1 second before next poll
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error(t("cameraCapture.taskTimedOut"));
  };

  const processFile = async (file: File) => {
    setUploading(true);
    const formData = new FormData();

    // Default source logic: if explicitly provided use it, otherwise detect from capture prop
    const effectiveSource = source || (capture === "environment" ? "scanner_camera" : "user_upload");

    try {
      if (mode === "gallery" && manifestation_id) {
        // Mode 3: Upload an additional scan to the gallery
        formData.append("image", file);
        formData.append("label", galleryLabel || "other");
        formData.append("source", effectiveSource);

        await apiClient.post(`/manifestations/${manifestation_id}/images`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        if (onGalleryUploadComplete) onGalleryUploadComplete();
      } else if (manifestation_id) {
        // Mode 1: Upload a user-contributed cover for a known manifestation
        formData.append("cover", file);
        formData.append("format", format);
        formData.append("source", effectiveSource);

        await apiClient.post(`/manifestations/${manifestation_id}/cover`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        if (onUploadComplete) onUploadComplete();
      } else {
        // Mode 2: OCR / Vision Metadata Extraction (Asynchronous)
        formData.append("cover", file);
        formData.append("format", format);
        formData.append("source", effectiveSource);

        const response = await apiClient.post<ApiEnvelope<{ task_id: string }>>(`/vision/extract`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
          signal:
            typeof AbortSignal !== "undefined" && "timeout" in AbortSignal ? AbortSignal.timeout(10000) : undefined,
        });

        const envelope = response.data;
        if (envelope.success && envelope.data?.task_id) {
          // Transition to polling
          const result = await startPolling(envelope.data.task_id);
          if (onExtractComplete) onExtractComplete(result, file, format);
        } else {
          toast.error(envelope.error ?? t("cameraCapture.visionSubmissionFailed"));
          if (onExtractionFailure) onExtractionFailure();
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t("cameraCapture.processImageFailed");
      toast.error(message);
      console.error("Failed to process cover image", error);
      if (onExtractionFailure) onExtractionFailure();
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
      toast.error(t("cameraCapture.invalidImageFile"));
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
  const isDesktopMode = !inline && (hasCamera === false || capture === false);

  const inputNode = (
    <input
      type="file"
      accept="image/*"
      {...(capture !== false && hasCamera !== false ? { capture } : {})}
      ref={fileInputRef}
      onChange={handleCapture}
      className="hidden"
    />
  );

  const confirmNode = confirmTitle && (
    <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{confirmTitle}</AlertDialogTitle>
          <AlertDialogDescription>{confirmMessage}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("cameraCapture.cancel")}</AlertDialogCancel>
          <AlertDialogAction onClick={handleConfirmAction}>{t("cameraCapture.continue")}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );

  if (inline) {
    return (
      <>
        {inputNode}
        <Button onClick={handleClick} disabled={uploading} variant={variant || "outline"} className={buttonClassName}>
          {uploading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {t("cameraCapture.processing")}
            </>
          ) : (
            <>
              {icon || <Camera className="mr-2 h-4 w-4" />}
              {label ?? t("cameraCapture.snapCover")}
            </>
          )}
        </Button>
        {confirmNode}
      </>
    );
  }

  return (
    <div
      className={`w-full relative ${className ?? ""} ${
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
      {uploading && (
        <div
          data-testid="scanner-uploading-overlay"
          className="absolute inset-0 z-20 flex flex-col items-center justify-center rounded-xl bg-background/90 backdrop-blur-sm p-4 text-center"
        >
          <div className="relative flex items-center justify-center mb-4">
            <div className="absolute h-14 w-14 rounded-full border-4 border-primary/30 border-t-transparent animate-[spin_1.5s_linear_infinite]" />
            <div className="h-10 w-10 rounded-full border-4 border-primary border-b-transparent animate-[spin_1s_linear_infinite_reverse]" />
          </div>
          <p className="animate-pulse text-sm font-semibold text-foreground">{t("cameraCapture.processingImage")}</p>
          <p className="text-xs text-muted-foreground mt-1">{t("cameraCapture.extractingDetails")}</p>
        </div>
      )}

      {inputNode}

      {isDesktopMode ? (
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <UploadCloud
            className={`h-10 w-10 ${isDragging ? "text-primary animate-bounce" : "text-muted-foreground"}`}
          />
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium">{t("cameraCapture.dragDropCover")}</p>
            <p className="text-xs text-muted-foreground">{t("cameraCapture.orBrowse")}</p>
          </div>
          <Button onClick={handleClick} disabled={uploading} className="mt-2">
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t("cameraCapture.processing")}
              </>
            ) : (
              t("cameraCapture.browseFiles")
            )}
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-4 w-full">
          <Button
            onClick={handleClick}
            disabled={uploading}
            variant={variant || "outline"}
            className={buttonClassName || "w-full"}
          >
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t("cameraCapture.processing")}
              </>
            ) : (
              <>
                {icon || <Camera className="mr-2 h-4 w-4" />}
                {label ?? t("cameraCapture.snapCover")}
              </>
            )}
          </Button>
        </div>
      )}

      {confirmNode}
    </div>
  );
}
