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

const SAMPLE_META = {
  Title: "Dune",
  Authors: ["Frank Herbert"],
  Publisher: "Chilton Books",
  Year: "1965",
  "ISBN-13": "9780441013593",
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
    expect(screen.getByText("Item Found")).toBeInTheDocument();
  });

  it("calls onDismiss when the header X button is clicked", () => {
    const onDismiss = vi.fn();
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={onDismiss} />);
    // Testing the UI interaction of clicking the close icon button
    fireEvent.click(screen.getByRole("button", { name: "" }) as HTMLElement); 
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("calls onDismiss when the bottom Dismiss button is clicked", () => {
    const onDismiss = vi.fn();
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("calls apiClient.post to /scan and shows success toast when 'Add to Library' succeeds", async () => {
    mockApiPost.mockResolvedValueOnce({ data: { success: true, data: { item_id: 99, manifestation_id: 100 } } });
    render(<SuccessCard isbn="9780441013593" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    
    fireEvent.click(screen.getByRole("button", { name: /add to library/i }));
    
    await waitFor(() => {
      // Assert that we correctly call the unified endpoint with barcode and format
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
    
    fireEvent.click(screen.getByRole("button", { name: /add to library/i }));
    
    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith("Network error");
    });
  });

  it("displays the barcode under the title", () => {
    render(<SuccessCard isbn="074646493524" meta={SAMPLE_META} onDismiss={vi.fn()} />);
    expect(screen.getByText(/barcode: 074646493524/i)).toBeInTheDocument();
  });
});
