'use client';

import React from 'react';
import ReactCrop, { type Crop, type PixelCrop, centerCrop, makeAspectCrop } from 'react-image-crop';

interface CoverCanvasProps {
  imgRef: React.RefObject<HTMLImageElement | null>;
  imageUrl: string;
  crop: Crop | undefined;
  setCrop: (crop: Crop) => void;
  setCompletedCrop: (crop: PixelCrop) => void;
  aspect: number | undefined;
  rotation: number;
  flipH: boolean;
  flipV: boolean;
}

/**
 * Generates a crop centered on the image with the specified aspect ratio.
 *
 * @param mediaWidth - The width of the media element.
 * @param mediaHeight - The height of the media element.
 * @param aspect - The target aspect ratio.
 * @returns The resulting crop configuration.
 */
function centerAspectCrop(mediaWidth: number, mediaHeight: number, aspect: number) {
  return centerCrop(
    makeAspectCrop({ unit: '%', width: 90 }, aspect, mediaWidth, mediaHeight),
    mediaWidth,
    mediaHeight
  );
}

/**
 * Canvas component that renders the cropped image with ReactCrop.
 *
 * @param props - Component props containing crop configuration and source image.
 * @returns The rendered components layout.
 */
export function CoverCanvas({ imgRef, imageUrl, crop, setCrop, setCompletedCrop, aspect, rotation, flipH, flipV }: CoverCanvasProps) {
  const onImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    if (aspect) {
      const { width, height } = e.currentTarget;
      setCrop(centerAspectCrop(width, height, aspect));
    }
  };

  return (
    <div className="relative shadow-lg border bg-background rounded-md overflow-hidden">
      <ReactCrop
        crop={crop}
        onChange={(_, percentCrop) => setCrop(percentCrop)}
        onComplete={(c) => setCompletedCrop(c)}
        aspect={aspect}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={imgRef as React.RefObject<HTMLImageElement>}
          src={imageUrl}
          alt="Source preview"
          onLoad={onImageLoad}
          style={{ transform: `scale(${flipH ? -1 : 1}, ${flipV ? -1 : 1}) rotate(${rotation}deg)` }}
          className="max-h-[70vh] object-contain"
          crossOrigin="anonymous"
        />
      </ReactCrop>
    </div>
  );
}
