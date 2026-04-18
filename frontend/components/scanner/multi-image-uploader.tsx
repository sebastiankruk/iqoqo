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

interface MultiImageUploaderProps {
  manifestationId: number;
  onUploadComplete: () => void;
}

/**
 * Component for uploading additional manifestation scans (disc, inlay, etc.).
 *
 * @param root0 - The props object
 * @param root0.manifestationId - ID of the manifestation to attach images to
 * @param root0.onUploadComplete - Callback when upload finishes
 * @returns {JSX.Element} The uploader UI
 */
export function MultiImageUploader({ manifestationId, onUploadComplete }: MultiImageUploaderProps) {
  const [label, setLabel] = useState<"front" | "back" | "disc" | "inlay" | "box" | "other">("disc");
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
      // Invalidate both manifestation detail and manifestations list queries to ensure UI refreshes everywhere
      await queryClient.invalidateQueries({ queryKey: ["manifestation", manifestationId] });
      await queryClient.invalidateQueries({ queryKey: ["manifestations"] });
      // Reset input
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
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setLabel(e.target.value as typeof label)}
          disabled={isUploading}
          className="text-xs bg-transparent border-none focus:ring-0 cursor-pointer font-semibold text-primary"
        >
          <option value="disc">Disc / Vinyl</option>
          <option value="inlay">Inlay / Booklet</option>
          <option value="back">Back Cover</option>
          <option value="box">Box</option>
          <option value="front">Front Cover</option>
          <option value="other">Other</option>
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
