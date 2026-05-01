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

import React, { useEffect } from "react";
import ReactCrop, { type Crop, type PixelCrop, centerCrop, makeAspectCrop } from "react-image-crop";

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
 * @param {number} mediaWidth - The width of the media element.
 * @param {number} mediaHeight - The height of the media element.
 * @param {number} aspect - The target aspect ratio.
 * @returns {import('react-image-crop').Crop} The resulting crop configuration.
 */
function centerAspectCrop(mediaWidth: number, mediaHeight: number, aspect: number) {
  return centerCrop(makeAspectCrop({ unit: "%", width: 90 }, aspect, mediaWidth, mediaHeight), mediaWidth, mediaHeight);
}

/**
 * Canvas component that renders the cropped image with ReactCrop.
 *
 * @param {Object} props - Component props.
 * @param {React.RefObject<HTMLImageElement>} props.imgRef - Reference to the image.
 * @param {string} props.imageUrl - Source image URL.
 * @param {import('react-image-crop').Crop | undefined} props.crop - Current crop.
 * @param {Function} props.setCrop - Set crop function.
 * @param {Function} props.setCompletedCrop - Set completed crop function.
 * @param {number | undefined} props.aspect - Aspect ratio.
 * @param {number} props.rotation - Rotation.
 * @param {boolean} props.flipH - Horizontal flip.
 * @param {boolean} props.flipV - Vertical flip.
 * @returns {JSX.Element} The rendered components layout.
 */
export function CoverCanvas({
  imgRef,
  imageUrl,
  crop,
  setCrop,
  setCompletedCrop,
  aspect,
  rotation,
  flipH,
  flipV,
}: CoverCanvasProps) {
  const onImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    if (aspect) {
      const { width, height } = e.currentTarget;
      setCrop(centerAspectCrop(width, height, aspect));
    }
  };

  // Re-calculate crop when aspect ratio changes to ensure dashed lines update immediately
  useEffect(() => {
    if (imgRef.current && aspect) {
      const { width, height } = imgRef.current;
      setCrop(centerAspectCrop(width, height, aspect));
    }
  }, [aspect, imgRef, setCrop]);

  return (
    <div className="relative shadow-lg border bg-background rounded-md overflow-hidden">
      <ReactCrop
        crop={crop}
        onChange={(_, percentCrop) => setCrop(percentCrop)}
        onComplete={c => setCompletedCrop(c)}
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
        />
      </ReactCrop>
    </div>
  );
}
