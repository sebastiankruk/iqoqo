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

import React from "react";
import { render, waitFor, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MultiImageUploader } from "@/components/scanner/multi-image-uploader";
import { apiClient } from "@/lib/api/client";
import { useQueryClient } from "@tanstack/react-query";

// Mock existing project tooling
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: vi.fn(),
}));

describe("MultiImageUploader", () => {
  const mockInvalidateQueries = vi.fn();
  const mockOnUploadComplete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useQueryClient).mockReturnValue({
      invalidateQueries: mockInvalidateQueries,
    } as unknown as ReturnType<typeof useQueryClient>);
  });

  it("uploads image successfully, invalidates queries, and calls onUploadComplete", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { success: true } });

    render(<MultiImageUploader manifestationId={999} onUploadComplete={mockOnUploadComplete} />);

    // Grab the hidden/standard file input
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();

    // Trigger the upload process
    const file = new File(["dummy content"], "test-disc.jpg", { type: "image/jpeg" });
    await userEvent.upload(fileInput, file);

    // Assert the API was hit
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledTimes(1);
    });

    // Assert cache invalidations occurred correctly
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ["manifestation", 999] });
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ["manifestations"] });

    // Assert the parent callback was triggered
    expect(mockOnUploadComplete).toHaveBeenCalledOnce();
  });

  it("renders both Browse and Snap buttons", async () => {
    render(<MultiImageUploader manifestationId={999} onUploadComplete={mockOnUploadComplete} />);

    expect(screen.getByText("Browse")).toBeInTheDocument();
    expect(screen.getByText("Snap")).toBeInTheDocument();
  });

  it("defaults label to 'front' when currentItemFormat is 'book'", async () => {
    render(
      <MultiImageUploader manifestationId={999} currentItemFormat="book" onUploadComplete={mockOnUploadComplete} />
    );
    expect(screen.getByRole("combobox")).toHaveValue("front");
  });

  it("defaults label to 'disc' when currentItemFormat is 'cd'", async () => {
    render(<MultiImageUploader manifestationId={999} currentItemFormat="cd" onUploadComplete={mockOnUploadComplete} />);
    expect(screen.getByRole("combobox")).toHaveValue("disc");
  });

  it("defaults label to 'box' when currentItemFormat is 'boardgame'", async () => {
    render(
      <MultiImageUploader manifestationId={999} currentItemFormat="boardgame" onUploadComplete={mockOnUploadComplete} />
    );
    expect(screen.getByRole("combobox")).toHaveValue("box");
  });
});
