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

/** Max pixel edge for vision/OCR extraction (~11MP keeps small ISSN/barcode glyphs crisp). */
export const VISION_MAX_DIMENSION = 3840;
/** JPEG quality for vision/OCR extraction uploads. */
export const VISION_JPEG_QUALITY = 0.9;

/** Max pixel edge for persisted cover and gallery image uploads. */
export const COVER_MAX_DIMENSION = 1280;
/** JPEG quality for persisted cover and gallery image uploads. */
export const COVER_JPEG_QUALITY = 0.88;

export interface ResizeImageOptions {
  /** Largest allowed width or height in pixels. */
  maxDimension?: number;
  /** Output JPEG quality between 0 and 1. */
  quality?: number;
}

interface DecodedImage {
  width: number;
  height: number;
  draw: (ctx: CanvasRenderingContext2D, width: number, height: number) => void;
  cleanup: () => void;
}

/** Normalize image filename extension to `.jpg` for JPEG re-encoded uploads. */
function replaceWithJpgExtension(filename: string): string {
  const clean = filename.trim() || "cover.jpg";
  if (/\.(jpe?g|png|webp|gif|bmp|heic|heif)$/i.test(clean)) {
    return clean.replace(/\.[^.]+$/, ".jpg");
  }
  return `${clean}.jpg`;
}

/** Decode a browser image File using createImageBitmap or an HTMLImageElement fallback. */
async function decodeImageFile(file: File): Promise<DecodedImage | null> {
  if (typeof createImageBitmap === "function") {
    try {
      const bitmap = await createImageBitmap(file);
      return {
        width: bitmap.width,
        height: bitmap.height,
        draw: (ctx, width, height) => ctx.drawImage(bitmap, 0, 0, width, height),
        cleanup: () => {
          if (typeof bitmap.close === "function") bitmap.close();
        },
      };
    } catch {
      // Fall through to HTMLImageElement loader below
    }
  }

  if (typeof Image === "undefined" || typeof URL === "undefined" || typeof URL.createObjectURL !== "function") {
    return null;
  }

  const objectUrl = URL.createObjectURL(file);
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const element = new Image();
      timer = setTimeout(() => reject(new Error("Image decode timeout")), 2000);
      element.onload = () => resolve(element);
      element.onerror = () => reject(new Error("Image decode failed"));
      element.src = objectUrl;
    });
    return {
      width: img.naturalWidth || img.width,
      height: img.naturalHeight || img.height,
      draw: (ctx, width, height) => ctx.drawImage(img, 0, 0, width, height),
      cleanup: () => URL.revokeObjectURL(objectUrl),
    };
  } catch {
    URL.revokeObjectURL(objectUrl);
    return null;
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

/**
 * Downscale an image file client-side before upload so high-megapixel phone
 * photos do not exhaust upload limits or backend image pixel ceilings.
 *
 * Returns the original File unchanged when decoding/canvas is unavailable
 * (e.g. non-image files, SSR, or synthetic headless test runtimes) or when
 * the image is already compact.
 */
export async function resizeImageFile(file: File, options: ResizeImageOptions = {}): Promise<File> {
  const maxDimension = options.maxDimension ?? COVER_MAX_DIMENSION;
  const quality = options.quality ?? COVER_JPEG_QUALITY;

  if (!file || !file.type.startsWith("image/") || typeof document === "undefined") {
    return file;
  }

  // Feature-detect 2D canvas upfront so runtimes without canvas (SSR/jsdom)
  // short-circuit immediately instead of stalling on blob: Image decode.
  const canvas = document.createElement("canvas");
  const ctx = typeof canvas.getContext === "function" ? canvas.getContext("2d") : null;
  if (!ctx) {
    return file;
  }

  const decoded = await decodeImageFile(file);
  if (!decoded) {
    return file;
  }

  try {
    const { width, height } = decoded;
    if (width <= 0 || height <= 0) {
      return file;
    }

    const longestSide = Math.max(width, height);
    // Keep already-compact JPEGs untouched to avoid unnecessary recompression.
    if (longestSide <= maxDimension && file.type === "image/jpeg" && file.size <= 1_500_000) {
      return file;
    }

    const scale = longestSide > maxDimension ? maxDimension / longestSide : 1;
    const targetWidth = Math.max(1, Math.round(width * scale));
    const targetHeight = Math.max(1, Math.round(height * scale));

    canvas.width = targetWidth;
    canvas.height = targetHeight;

    decoded.draw(ctx, targetWidth, targetHeight);

    const blob = await new Promise<Blob | null>(resolve => {
      canvas.toBlob(result => resolve(result), "image/jpeg", quality);
    });
    if (!blob) {
      return file;
    }

    // If dimensions weren't reduced and the re-encoded JPEG grew larger, keep original.
    if (scale === 1 && blob.size >= file.size) {
      return file;
    }

    return new File([blob], replaceWithJpgExtension(file.name), {
      type: "image/jpeg",
      lastModified: file.lastModified || Date.now(),
    });
  } catch {
    return file;
  } finally {
    decoded.cleanup();
  }
}
