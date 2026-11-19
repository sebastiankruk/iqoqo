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
import { afterEach, describe, expect, it, vi } from "vitest";
import { COVER_MAX_DIMENSION, resizeImageFile, VISION_MAX_DIMENSION } from "@/lib/image-resize";

describe("resizeImageFile", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns non-image files untouched", async () => {
    const textFile = new File(["hello"], "notes.txt", { type: "text/plain" });
    const result = await resizeImageFile(textFile);
    expect(result).toBe(textFile);
  });

  it("falls back to the original file when browser image decoding is unavailable", async () => {
    const imgFile = new File([new Uint8Array([1, 2, 3])], "cover.jpg", { type: "image/jpeg" });
    const result = await resizeImageFile(imgFile);
    expect(result).toBe(imgFile);
  });

  it("downscales high-megapixel cover photos to COVER_MAX_DIMENSION JPEG", async () => {
    const closeMock = vi.fn();
    vi.stubGlobal("createImageBitmap", vi.fn().mockResolvedValue({ width: 6144, height: 8160, close: closeMock }));

    const drawImageMock = vi.fn();
    const origCreateElement = document.createElement.bind(document);
    let createdCanvas: HTMLCanvasElement | null = null;
    vi.spyOn(document, "createElement").mockImplementation(((tagName: string) => {
      const el = origCreateElement(tagName);
      if (tagName === "canvas") {
        createdCanvas = el as HTMLCanvasElement;
        (el as HTMLCanvasElement).getContext = vi.fn(() => ({
          drawImage: drawImageMock,
        })) as unknown as HTMLCanvasElement["getContext"];
        (el as HTMLCanvasElement).toBlob = vi.fn((cb: BlobCallback) => {
          cb(new Blob([new Uint8Array(120_000)], { type: "image/jpeg" }));
        });
      }
      return el;
    }) as typeof document.createElement);

    const hugeFile = new File([new Uint8Array(8_600_000)], "PXL_cover.png", { type: "image/png" });
    const resized = await resizeImageFile(hugeFile, { maxDimension: COVER_MAX_DIMENSION });

    expect(createdCanvas).not.toBeNull();
    expect(createdCanvas!.height).toBe(COVER_MAX_DIMENSION);
    expect(createdCanvas!.width).toBe(Math.round(6144 * (COVER_MAX_DIMENSION / 8160)));
    expect(drawImageMock).toHaveBeenCalledTimes(1);
    expect(closeMock).toHaveBeenCalledTimes(1);
    expect(resized.name).toBe("PXL_cover.jpg");
    expect(resized.type).toBe("image/jpeg");
    expect(resized.size).toBe(120_000);
  });

  it("preserves higher resolution ceiling for vision OCR extraction", async () => {
    vi.stubGlobal("createImageBitmap", vi.fn().mockResolvedValue({ width: 6144, height: 8160, close: vi.fn() }));

    const origCreateElement = document.createElement.bind(document);
    let createdCanvas: HTMLCanvasElement | null = null;
    vi.spyOn(document, "createElement").mockImplementation(((tagName: string) => {
      const el = origCreateElement(tagName);
      if (tagName === "canvas") {
        createdCanvas = el as HTMLCanvasElement;
        (el as HTMLCanvasElement).getContext = vi.fn(() => ({
          drawImage: vi.fn(),
        })) as unknown as HTMLCanvasElement["getContext"];
        (el as HTMLCanvasElement).toBlob = vi.fn((cb: BlobCallback) => {
          cb(new Blob([new Uint8Array(950_000)], { type: "image/jpeg" }));
        });
      }
      return el;
    }) as typeof document.createElement);

    const hugeFile = new File([new Uint8Array(8_600_000)], "magazine.jpg", { type: "image/jpeg" });
    await resizeImageFile(hugeFile, { maxDimension: VISION_MAX_DIMENSION });

    expect(createdCanvas!.height).toBe(VISION_MAX_DIMENSION);
    expect(createdCanvas!.width).toBe(Math.round(6144 * (VISION_MAX_DIMENSION / 8160)));
  });
});
