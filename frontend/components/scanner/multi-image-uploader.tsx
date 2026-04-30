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

import React, { useState } from "react";
import { toast } from "sonner";
import { CopyPlus, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";
import {
  GLOBAL_IMAGE_TYPES,
  CATEGORY_IMAGE_TYPES,
  MEDIA_HIERARCHY,
  MEDIA_CATEGORIES,
  FORMAT_ALIAS_TO_CATEGORY,
  CATEGORY_DEFAULT_IMAGE_TYPE,
  MediaCategory,
  ImageType,
} from "@/types/frbr";

interface MultiImageUploaderProps {
  manifestationId: number;
  currentItemFormat?: string;
  onUploadComplete: () => void;
}

/**
 * Component for uploading additional manifestation scans (disc, inlay, etc.).
 * @param root0 - Component props.
 * @param root0.manifestationId - ID of the manifestation to upload scans for.
 * @param root0.currentItemFormat - Current item format string for label defaults.
 * @param root0.onUploadComplete - Callback invoked after a successful upload.
 * @returns The multi-image uploader UI.
 */
export function MultiImageUploader({ manifestationId, currentItemFormat, onUploadComplete }: MultiImageUploaderProps) {
  // Find category for current format to show context-aware labels
  const itemCategory =
    (Object.entries(MEDIA_HIERARCHY).find(([, info]) =>
      info.formats.some(f => f.id === currentItemFormat)
    )?.[0] as MediaCategory) || MEDIA_CATEGORIES[0];

  // Resolve format/alias → category via the generated SSoT map, fallback to hierarchy-based category
  const resolvedCategory = FORMAT_ALIAS_TO_CATEGORY[currentItemFormat?.toLowerCase() || ""] || itemCategory;

  const availableImageTypes = [...GLOBAL_IMAGE_TYPES, ...(CATEGORY_IMAGE_TYPES[resolvedCategory] || [])];

  const getDefaultLabel = (): ImageType => {
    return (CATEGORY_DEFAULT_IMAGE_TYPE[resolvedCategory] || GLOBAL_IMAGE_TYPES[0]) as ImageType;
  };

  const [label, setLabel] = useState<ImageType>(getDefaultLabel());
  const [isUploading, setIsUploading] = useState(false);
  const queryClient = useQueryClient();

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("image", file);
    formData.append("label", label);

    try {
      await apiClient.post(`/manifestations/${manifestationId}/images`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`${label} image uploaded successfully!`);
      await queryClient.invalidateQueries({ queryKey: ["manifestation", manifestationId] });
      await queryClient.invalidateQueries({ queryKey: ["manifestations"] });
      e.target.value = "";
      onUploadComplete();
    } catch (error) {
      toast.error("Failed to upload image.");
      console.error(error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2 p-3 rounded-lg border bg-muted/30">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Additional Scans</span>
        <select
          value={label}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLabel(e.target.value as ImageType)}
          disabled={isUploading}
          className="text-xs bg-transparent border-none focus:ring-0 cursor-pointer font-semibold text-primary"
        >
          {availableImageTypes.map(t => (
            <option key={t} value={t}>
              {t.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
            </option>
          ))}
        </select>
      </div>

      <div className="relative">
        <input
          type="file"
          accept="image/*"
          onChange={handleUpload}
          disabled={isUploading}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
          id="gallery-upload"
        />
        <Button
          variant="outline"
          size="sm"
          disabled={isUploading}
          className="w-full h-8 text-[11px] font-semibold flex items-center justify-center gap-2 border-dashed"
        >
          {isUploading ? <Loader2 className="h-3 w-3 animate-spin" /> : <CopyPlus className="h-3 w-3" />}
          {isUploading ? "Uploading..." : `Upload ${label} image`}
        </Button>
      </div>
    </div>
  );
}
