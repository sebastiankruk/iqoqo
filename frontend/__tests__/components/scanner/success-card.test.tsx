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
/**
 * Tests for the SuccessCard component.
 *
 * Simulates post-scan state: the card receives isbn + meta props, lets the
 * user dismiss the result or add the item to the library.
 *
 * Mocks:
 * - next/navigation (useRouter) – global in vitest.setup.ts
 * - sonner (toast) – global in vitest.setup.ts
 * - @/lib/api/client (apiClient.post) – per-test via the mock factory below
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import type { IsbnMeta } from "@/types/frbr";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
  apiFetch: vi.fn(),
}));

import { apiClient } from "@/lib/api/client";
import { SuccessCard } from "@/components/scanner/success-card";

const mockPush = vi.fn();
const mockApiPost = vi.mocked(apiClient.post);
const mockToastSuccess = vi.mocked(toast.success);
const mockToastError = vi.mocked(toast.error);

const SAMPLE_META: IsbnMeta = {
  Title: "Dune",
  Authors: ["Frank Herbert"],
  title: "Dune",
  author: "Frank Herbert",
  Publisher: "Chilton Books",
  Year: "1965",
  "ISBN-13": "9780441013593",
  isbn: "9780441013593",
  format: "book"
};

describe("SuccessCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useRouter).mockReturnValue({
      push: mockPush,
      replace: vi.fn(),
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    } as ReturnType<typeof useRouter>);
  });

  it("displays the item title from meta", () => {
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText("Dune")).toBeInTheDocument();
  });

  it("displays the author name", () => {
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText("Frank Herbert")).toBeInTheDocument();
  });

  it("shows an 'Item Found' success header", () => {
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText("Successfully Found!")).toBeInTheDocument();
  });

  it("calls onDismiss when the header X button is clicked", () => {
    const onDismiss = vi.fn();
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={onDismiss} />);
    // Testing the UI interaction of clicking the close icon button
    fireEvent.click(screen.getByRole("button", { name: "Close" })); 
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("calls onDismiss when the bottom Dismiss button is clicked", () => {
    const onDismiss = vi.fn();
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole("button", { name: "Scan Another" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("calls apiClient.post to /scan and shows success toast when 'Add to Library' succeeds", async () => {
    mockApiPost.mockResolvedValueOnce({ data: { success: true, data: { item_id: 99, manifestation_id: 100 } } });
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    
    // Explicitly clear mock to avoid interference from earlier renders in this file
    mockApiPost.mockClear();
    
    fireEvent.click(screen.getByRole("button", { name: /add to collection/i }));
    
    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith("/scan", { 
        barcode: "9780441013593", 
        format: "book" 
      });
      expect(mockToastSuccess).toHaveBeenCalledWith('"Dune" added to your library!');
      expect(mockPush).toHaveBeenCalledWith("/item/99");
    });
  });

  it("shows an error toast when 'Add to Library' fails", async () => {
    mockApiPost.mockRejectedValueOnce(new Error("Network error"));
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    
    fireEvent.click(screen.getByRole("button", { name: /add to collection/i }));
    
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Network error");
    });
  });

  it("displays the barcode under the title", () => {
    render(<SuccessCard isbn="074646493524" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText("074646493524")).toBeInTheDocument();
  });

  it("renders correctly with audio barcode fallback", () => {
    const meta: IsbnMeta = {
      Title: "Dark Side of the Moon",
      Authors: ["Pink Floyd"],
      title: "Dark Side of the Moon",
      author: "Pink Floyd",
      format: "audio",
      barcode: "077774600125"
    };

    render(<SuccessCard isbn="077774600125" meta={meta} onDismiss={vi.fn()} />);

    expect(screen.getByText("Dark Side of the Moon")).toBeInTheDocument();
    expect(screen.getByText("Pink Floyd")).toBeInTheDocument();
    expect(screen.getByText("077774600125")).toBeInTheDocument();
    expect(screen.getByText("Audio Media")).toBeInTheDocument();
    expect(screen.getByText("AUDIO")).toBeInTheDocument(); // Uppercase check
  });

  it("shows a warning when no standard identifier is found", () => {
    const meta: IsbnMeta = {
      Title: "Generic Item",
      Authors: ["Unknown"],
      format: "book"
    };

    render(<SuccessCard isbn="" meta={meta} onDismiss={vi.fn()} />);

    expect(screen.getByText(/no standard ISBN\/Barcode found/i)).toBeInTheDocument();
  });

  it("applies correct aspect ratio classes based on format", () => {
    const { container: audioContainer } = render(
      <SuccessCard isbn="123" meta={{ format: "audio" } as IsbnMeta} onDismiss={vi.fn()} />
    );
    expect(audioContainer.querySelector(".aspect-square")).toBeInTheDocument();

    const { container: bookContainer } = render(
      <SuccessCard isbn="123" meta={{ format: "book" } as IsbnMeta} onDismiss={vi.fn()} />
    );
    expect(bookContainer.querySelector(".aspect-\\[2\\/3\\]")).toBeInTheDocument();
  });
});
