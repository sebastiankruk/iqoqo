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

import React, { useRef, useState } from "react";
import { Camera, ImagePlus, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { apiClient } from "@/lib/api/client";
import { Button, type ButtonVariant } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { MediaFormat } from "@/types/frbr";

/** Props for CoverUploadPicker component */
export interface CoverUploadPickerProps {
  /** If set, uploads cover for this manifestation */
  manifestation_id?: number;
  /** Format of the media item (e.g. book, cd, vinyl) */
  format?: MediaFormat | string;
  /** Custom label for button (e.g. "Contribute Cover" or "Replace Cover") */
  label?: string;
  /** Optional icon to display before label */
  icon?: React.ReactNode;
  /** Dialog confirmation title if replacement confirmation required */
  confirmTitle?: string;
  /** Dialog confirmation description */
  confirmMessage?: string;
  /** Callback fired after successful upload */
  onUploadComplete?: () => void;
  /** Button visual variant */
  variant?: ButtonVariant;
  /** Wrapper class name */
  className?: string;
  /** Direct class name on the trigger button */
  buttonClassName?: string;
  /** If true, inline layout */
  inline?: boolean;
  /** If disabled */
  disabled?: boolean;
  /** Source identifier override */
  source?: string;
}

/**
 * Dual-source cover art contributor and replacer.
 * Presents a single unified button that opens a selection modal,
 * allowing collectors to pick between camera snapshot and device photo gallery.
 *
 * @param props - Component configuration props.
 * @returns {JSX.Element} Rendered button with dual-source upload trigger.
 */
export function CoverUploadPicker({
  manifestation_id,
  format = "book",
  label,
  icon,
  confirmTitle,
  confirmMessage,
  onUploadComplete,
  variant = "outline",
  className,
  buttonClassName,
  disabled = false,
  source,
}: CoverUploadPickerProps) {
  const t = useTranslations("scanner");
  const [uploading, setUploading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);

  /**
   * Upload the selected cover image file to the manifestation endpoint.
   */
  const processFile = async (file: File, uploadSource: "scanner_camera" | "user_upload") => {
    if (!manifestation_id) return;
    setUploading(true);

    const formData = new FormData();
    formData.append("cover", file);
    formData.append("format", String(format));
    formData.append("source", source || uploadSource);

    try {
      await apiClient.post(`/manifestations/${manifestation_id}/cover`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (onUploadComplete) {
        onUploadComplete();
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t("cameraCapture.processImageFailed");
      toast.error(message);
      console.error("Failed to process cover image", error);
    } finally {
      setUploading(false);
      if (cameraInputRef.current) cameraInputRef.current.value = "";
      if (galleryInputRef.current) galleryInputRef.current.value = "";
    }
  };

  const handleCapture = (
    event: React.ChangeEvent<HTMLInputElement>,
    uploadSource: "scanner_camera" | "user_upload"
  ) => {
    const file = event.target.files?.[0];
    if (file) {
      processFile(file, uploadSource);
    }
  };

  const buttonContent = (
    <>
      {uploading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          {t("cameraCapture.processing")}
        </>
      ) : (
        <>
          {icon || <ImagePlus className="mr-2 h-4 w-4" />}
          {label ?? t("cameraCapture.snapCover")}
        </>
      )}
    </>
  );

  const dialogTitle = confirmTitle || label || t("cameraCapture.snapCover");
  const dialogDescription = confirmMessage || t("cameraCapture.chooseCoverSource");

  return (
    <div className={className} data-testid="cover-upload-picker">
      {/* Hidden native input for live camera capture */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/*"
        capture="environment"
        aria-label="Camera capture"
        data-testid="camera-file-input"
        onChange={e => handleCapture(e, "scanner_camera")}
        className="hidden"
      />

      {/* Hidden native input for filesystem / photo gallery picker */}
      <input
        ref={galleryInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/*"
        aria-label="Gallery upload"
        data-testid="gallery-file-input"
        onChange={e => handleCapture(e, "user_upload")}
        className="hidden"
      />

      <Button
        type="button"
        variant={variant}
        disabled={disabled || uploading}
        className={buttonClassName}
        onClick={() => setConfirmOpen(true)}
      >
        {buttonContent}
      </Button>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{dialogTitle}</AlertDialogTitle>
            <AlertDialogDescription>{dialogDescription}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex-col sm:flex-row gap-2">
            <AlertDialogCancel>{t("cameraCapture.cancel")}</AlertDialogCancel>
            <Button
              type="button"
              variant="outline"
              data-testid="confirm-take-photo"
              onClick={() => {
                setConfirmOpen(false);
                cameraInputRef.current?.click();
              }}
              className="flex items-center gap-1.5"
            >
              <Camera className="h-4 w-4" />
              {t("cameraCapture.takePhoto")}
            </Button>
            <Button
              type="button"
              data-testid="confirm-choose-gallery"
              onClick={() => {
                setConfirmOpen(false);
                galleryInputRef.current?.click();
              }}
              className="flex items-center gap-1.5"
            >
              <ImagePlus className="h-4 w-4" />
              {t("cameraCapture.chooseFromGallery")}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
