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

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AddToCollectionDropdown } from "@/components/collection/add-to-collection-dropdown";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";

// Mock apiClient and toast
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

describe("AddToCollectionDropdown", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AddToCollectionDropdown manifestationId={123} />
      </QueryClientProvider>
    );

  it("renders the button and shows options on click", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { success: true, collections: [] },
    });

    renderComponent();

    const button = screen.getByRole("button", { name: /add to collection/i });
    expect(button).toBeInTheDocument();

    // Click to open dropdown
    fireEvent.click(button);

    expect(screen.getByText("Add to Wishlist")).toBeInTheDocument();
    expect(screen.getByText("Add to My Library")).toBeInTheDocument();
  });

  it("succeeds when Add to Wishlist is clicked", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { success: true, collections: [] },
    });
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { item_id: null, intent_id: 1, manifestation_id: 123 } },
    });

    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: /add to collection/i }));

    const wishlistBtn = screen.getByText("Add to Wishlist");
    fireEvent.click(wishlistBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/manifestations/123/add", {
        collection_status: "wish_list",
      });
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Added to your wishlist!");
    });
  });

  it("succeeds when Add to My Library is clicked", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { success: true, collections: [] },
    });
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { item_id: 456, intent_id: null, manifestation_id: 123 } },
    });

    renderComponent();

    fireEvent.click(screen.getByRole("button", { name: /add to collection/i }));

    const libraryBtn = screen.getByText("Add to My Library");
    fireEvent.click(libraryBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/manifestations/123/add", {});
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Added to your collection!");
    });
  });
});
