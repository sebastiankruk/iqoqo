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

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CoverCanvas } from "@/components/admin/cover-editor/cover-canvas";
import React from "react";

describe("CoverCanvas Component", () => {
  const mockSetCrop = vi.fn();
  const mockSetCompletedCrop = vi.fn();
  const mockImgRef = {
    current: { width: 1000, height: 1500 },
  } as unknown as React.RefObject<HTMLImageElement>;

  it("re-calculates crop when aspect ratio changes", () => {
    const { rerender } = render(
      <CoverCanvas
        imgRef={mockImgRef}
        imageUrl="test.jpg"
        crop={undefined}
        setCrop={mockSetCrop}
        setCompletedCrop={mockSetCompletedCrop}
        aspect={2 / 3}
        rotation={0}
        flipH={false}
        flipV={false}
      />
    );

    // Initial load might trigger setCrop if onLoad is fired, but here we test prop update
    mockSetCrop.mockClear();

    // Re-render with a new aspect ratio (e.g., switching to 1:1 square)
    rerender(
      <CoverCanvas
        imgRef={mockImgRef}
        imageUrl="test.jpg"
        crop={undefined}
        setCrop={mockSetCrop}
        setCompletedCrop={mockSetCompletedCrop}
        aspect={1}
        rotation={0}
        flipH={false}
        flipV={false}
      />
    );
    // The useEffect should have triggered setCrop
    expect(mockSetCrop).toHaveBeenCalled();
    expect(screen.getByAltText("Source preview")).toBeInTheDocument();
  });
});
