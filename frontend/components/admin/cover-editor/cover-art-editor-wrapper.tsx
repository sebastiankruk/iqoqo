'use client';

import React, { useState, useRef } from 'react';
import { type PixelCrop } from 'react-image-crop';
import { CoverCanvas } from '@/components/admin/cover-editor/cover-canvas';
import { EditorToolbar } from '@/components/admin/cover-editor/editor-toolbar';
import { InfoSidebar } from '@/components/admin/cover-editor/info-sidebar';
import { uploadEntityCover } from '@/lib/api/admin';
import { toast } from 'sonner';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

/**
 * Component that wraps the Cover Art Editor logic and views.
 *
 * @returns The wrapper component for editing cover art.
 */
export function CoverArtEditorWrapper() {
  // Example dummy manifestation context: In reality this would be driven by the user selecting a manifestation, similar to ContentEditorWrapper
  const entityId = 1;
  const entityType = 'manifestation';
  const initialImageUrl = '/images/sample-cover-edit.jpg';

  const imgRef = useRef<HTMLImageElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [imageSrc, setImageSrc] = useState(initialImageUrl);
  const [crop, setCrop] = useState<any>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const [aspect, setAspect] = useState<number | undefined>(2 / 3);
  const [rotation, setRotation] = useState(0);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageSrc(URL.createObjectURL(file));
      setRotation(0);
      setFlipH(false);
      setFlipV(false);
      setCrop(undefined);
      setCompletedCrop(undefined);
    }
  };

  const handleSave = async (blob: Blob) => {
    try {
      setIsUploading(true);
      const response = await uploadEntityCover(entityType, entityId, blob);
      
      if (response.success) {
        toast.success('Cover art updated successfully!');
      } else {
        toast.error(response.error || 'Failed to upload.');
      }
    } catch (err: any) {
      toast.error(err.message || 'An error occurred.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cover Art Editor</CardTitle>
        <CardDescription>Upload, crop, zoom, and rotate cover art. Make sure bounding boxes represent actual media aspects.</CardDescription>
      </CardHeader>
      <CardContent>
        <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />

        <div className="flex bg-background border rounded-md overflow-hidden min-h-[500px]">
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            <EditorToolbar 
              aspect={aspect} 
              setAspect={setAspect} 
              setRotation={setRotation} 
              flipH={flipH} setFlipH={setFlipH}
              flipV={flipV} setFlipV={setFlipV}
            />
            <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-muted/30">
              <CoverCanvas 
                imgRef={imgRef}
                imageUrl={imageSrc}
                crop={crop}
                setCrop={setCrop}
                setCompletedCrop={setCompletedCrop}
                aspect={aspect}
                rotation={rotation}
                flipH={flipH}
                flipV={flipV}
              />
            </div>
          </div>
          <InfoSidebar 
            imgRef={imgRef}
            completedCrop={completedCrop}
            rotation={rotation}
            flipH={flipH}
            flipV={flipV}
            isUploading={isUploading}
            onSave={handleSave}
            onUploadSelect={() => fileInputRef.current?.click()}
          />
        </div>
      </CardContent>
    </Card>
  );
}
