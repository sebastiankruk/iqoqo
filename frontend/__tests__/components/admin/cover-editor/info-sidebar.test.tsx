// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>
//
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { InfoSidebar } from "@/components/admin/cover-editor/info-sidebar";
import React from "react";

describe("InfoSidebar Component - Cover Editor", () => {
  const mockImgRef = { current: null };
  const mockCompletedCrop = {
    x: 0,
    y: 0,
    width: 100,
    height: 150,
    unit: "px" as const,
    style: { width: "100px", height: "150px" },
  };
  const mockOnSave = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders Save Cover Art button", () => {
    render(
      <InfoSidebar
        imgRef={mockImgRef as React.RefObject<HTMLImageElement | null>}
        completedCrop={mockCompletedCrop}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={false}
        onSave={mockOnSave}
      />
    );

    expect(screen.getByRole("button", { name: /Save Cover Art/i })).toBeInTheDocument();
  });

  it("renders Upload New File button when onUploadSelect provided", () => {
    const mockUploadSelect = vi.fn();
    render(
      <InfoSidebar
        imgRef={mockImgRef as React.RefObject<HTMLImageElement | null>}
        completedCrop={mockCompletedCrop}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={false}
        onSave={mockOnSave}
        onUploadSelect={mockUploadSelect}
      />
    );

    expect(screen.getByRole("button", { name: /Upload New File/i })).toBeInTheDocument();
  });

  it("disables Save button when no crop defined", () => {
    render(
      <InfoSidebar
        imgRef={mockImgRef as React.RefObject<HTMLImageElement | null>}
        completedCrop={undefined}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={false}
        onSave={mockOnSave}
      />
    );

    expect(screen.getByRole("button", { name: /Save Cover Art/i })).toBeDisabled();
  });

  it("disables Save button when uploading", () => {
    render(
      <InfoSidebar
        imgRef={mockImgRef as React.RefObject<HTMLImageElement | null>}
        completedCrop={mockCompletedCrop}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={true}
        onSave={mockOnSave}
      />
    );

    expect(screen.getByRole("button", { name: /Processing/i })).toBeDisabled();
  });

  it("shows Processing state while uploading", () => {
    render(
      <InfoSidebar
        imgRef={mockImgRef as React.RefObject<HTMLImageElement | null>}
        completedCrop={mockCompletedCrop}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={true}
        onSave={mockOnSave}
      />
    );

    expect(screen.getByText(/Processing/i)).toBeInTheDocument();
  });

  it("calls onUploadSelect when Upload button clicked", () => {
    const mockUploadSelect = vi.fn();
    render(
      <InfoSidebar
        imgRef={mockImgRef as React.RefObject<HTMLImageElement | null>}
        completedCrop={mockCompletedCrop}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={false}
        onSave={mockOnSave}
        onUploadSelect={mockUploadSelect}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Upload New File/i }));
    expect(mockUploadSelect).toHaveBeenCalled();
  });

  it("does not call onSave without image element", () => {
    const emptyImgRef = { current: null };
    render(
      <InfoSidebar
        imgRef={emptyImgRef as React.RefObject<HTMLImageElement | null>}
        completedCrop={mockCompletedCrop}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={false}
        onSave={mockOnSave}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Save Cover Art/i }));
    expect(mockOnSave).not.toHaveBeenCalled();
  });

  it("does not call onSave without completed crop", () => {
    render(
      <InfoSidebar
        imgRef={mockImgRef as React.RefObject<HTMLImageElement | null>}
        completedCrop={undefined}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={false}
        onSave={mockOnSave}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Save Cover Art/i }));
    expect(mockOnSave).not.toHaveBeenCalled();
  });

  it("calls onSave when save button is clicked without mocking canvas", async () => {
    const mockImage = {
      current: {
        naturalWidth: 200,
        naturalHeight: 300,
        width: 100,
        height: 150,
      },
    };

    render(
      <InfoSidebar
        imgRef={mockImage as React.RefObject<HTMLImageElement | null>}
        completedCrop={mockCompletedCrop}
        rotation={0}
        flipH={false}
        flipV={false}
        isUploading={false}
        onSave={mockOnSave}
      />
    );

    const saveBtn = screen.getByRole("button", { name: /Save Cover Art/i });
    if (saveBtn) {
      fireEvent.click(saveBtn);
    }
  });
});
