"use client";

import React, { useRef, useState } from "react";
import { Camera, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api/client";

interface CameraCaptureProps {
  manifestationId: number;
  onUploadComplete?: () => void;
  className?: string;
}

export function CameraCapture({ manifestationId, onUploadComplete, className }: CameraCaptureProps) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCapture = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("cover", file);

    try {
      await apiClient.post(`/manifestations/${manifestationId}/cover`, formData);
      if (onUploadComplete) onUploadComplete();
    } catch (error) {
      console.error("Failed to upload cover", error);
    } finally {
      setUploading(false);
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
