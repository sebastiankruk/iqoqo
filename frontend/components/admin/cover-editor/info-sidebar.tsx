'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Save, Loader2, Upload } from 'lucide-react';
import { type PixelCrop } from 'react-image-crop';

interface InfoSidebarProps {
  imgRef: React.RefObject<HTMLImageElement | null>;
  completedCrop: PixelCrop | undefined;
  rotation: number;
  flipH: boolean;
  flipV: boolean;
  isUploading: boolean;
  onSave: (blob: Blob) => void;
  onUploadSelect?: () => void;
}

/**
 * Sidebar component that triggers the upload process and binds UI actions.
 *
 * @param props - Layout and upload handling configurations.
 * @returns The rendered sidebar pane.
 */
export function InfoSidebar({ imgRef, completedCrop, rotation, flipH, flipV, isUploading, onSave, onUploadSelect }: InfoSidebarProps) {
  
  const handleGenerateAndSave = async () => {
    const image = imgRef.current;
    if (!image || !completedCrop) return;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;
    
    canvas.width = Math.floor(completedCrop.width * scaleX);
    canvas.height = Math.floor(completedCrop.height * scaleY);

    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.scale(flipH ? -1 : 1, flipV ? -1 : 1);
    ctx.translate(-canvas.width / 2, -canvas.height / 2);

    ctx.drawImage(
      image,
      Math.floor(completedCrop.x * scaleX),
      Math.floor(completedCrop.y * scaleY),
      Math.floor(completedCrop.width * scaleX),
      Math.floor(completedCrop.height * scaleY),
      0,
      0,
      Math.floor(completedCrop.width * scaleX),
      Math.floor(completedCrop.height * scaleY)
    );

    canvas.toBlob(
      (blob) => { if (blob) onSave(blob); },
      'image/jpeg',
      0.9
    );
  };

  return (
    <div className="w-80 border-l bg-background p-4 flex flex-col gap-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground">Editor Actions</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {onUploadSelect && (
            <Button 
              className="w-full" 
              variant="outline"
              onClick={onUploadSelect} 
              disabled={isUploading}
            >
              <Upload className="mr-2 h-4 w-4" /> Upload New File
            </Button>
          )}
          <Button 
            className="w-full" 
            onClick={handleGenerateAndSave} 
            disabled={isUploading || !completedCrop}
          >
            {isUploading ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing...</>
            ) : (
              <><Save className="mr-2 h-4 w-4" /> Save Cover Art</>
            )}
          </Button>
        </CardContent>
      </Card>
      <div className="text-sm text-muted-foreground mt-4">
        <p>Ensure the cover correctly identifies the format.</p>
        <ul className="list-disc pl-4 mt-2">
            <li>1:1 for Vinyl/CD</li>
            <li>2:3 for standard Books/DVDs</li>
        </ul>
      </div>
    </div>
  );
}
