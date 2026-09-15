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

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { BulkAddToolbar, deriveStatusOptions } from "@/components/collection/bulk-add-toolbar";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";
import type { CatalogEntry } from "@/types/frbr";
import React from "react";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockItems: CatalogEntry[] = [
  {
    id: 1,
    title: "Book 1",
    content_type: "text",
    expression_id: 1,
    meta: {},
  } as unknown as CatalogEntry,
  {
    id: 2,
    title: "Audiobook 1",
    content_type: "audiobook",
    expression_id: 2,
    meta: {},
  } as unknown as CatalogEntry,
];

describe("BulkAddToolbar Component and Status Options", () => {
  let queryClient: QueryClient;
  let invalidateSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    vi.mocked(useQueryClient).mockReturnValue(queryClient);
  });

  it("deriveStatusOptions produces deduplicated options with distinct labels and payloads", () => {
    const options = deriveStatusOptions(mockItems);

    expect(options.length).toBeGreaterThan(0);

    // Ensure no duplicate keys or labels
    const keys = options.map(opt => `${opt.collectionStatus}:${opt.value}:${opt.label}`);
    const uniqueKeys = new Set(keys);
    expect(keys.length).toBe(uniqueKeys.size);

    // Verify "On shelf (no status)" has distinct empty value and collectionStatus available
    const onShelf = options.find(opt => opt.label.includes("On shelf"));
    expect(onShelf).toBeDefined();
    expect(onShelf?.value).toBe("");
    expect(onShelf?.collectionStatus).toBe("available");

    // Verify "Ordered" has collectionStatus ordered
    const ordered = options.find(opt => opt.label === "Ordered");
    expect(ordered).toBeDefined();
    expect(ordered?.collectionStatus).toBe("ordered");

    // Verify "Wish list" has collectionStatus wish_list
    const wishlist = options.find(opt => opt.collectionStatus === "wish_list");
    expect(wishlist).toBeDefined();
  });

  it("renders null when no items are selected", () => {
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <BulkAddToolbar selectedItems={[]} onClearSelection={vi.fn()} onSuccess={vi.fn()} />
      </QueryClientProvider>
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders toolbar with selection count and opens deduplicated option list", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BulkAddToolbar selectedItems={mockItems} onClearSelection={vi.fn()} onSuccess={vi.fn()} />
      </QueryClientProvider>
    );

    expect(screen.getByText("2 selected")).toBeInTheDocument();

    const openButton = screen.getByRole("button", { name: /add to collection as/i });
    fireEvent.click(openButton);

    const options = screen.getAllByRole("option");
    expect(options.length).toBe(4);
    expect(screen.getByText(/Want to Read \/ Listen/i)).toBeInTheDocument();
    expect(screen.getByText("Ordered")).toBeInTheDocument();
    expect(screen.getByText(/Read \/ Listened/i)).toBeInTheDocument();
    expect(screen.getByText("On shelf (no status)")).toBeInTheDocument();
  });

  it("submits bulk add request and invalidates queries on option click", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { item_ids: [10, 20], manifestation_ids: [1, 2] } },
    } as any);

    const onClearSelection = vi.fn();
    const onSuccess = vi.fn();

    render(
      <QueryClientProvider client={queryClient}>
        <BulkAddToolbar selectedItems={mockItems} onClearSelection={onClearSelection} onSuccess={onSuccess} />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: /add to collection as/i }));
    fireEvent.click(screen.getByText("On shelf (no status)"));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/items/bulk", {
        manifestation_ids: [1, 2],
        status: undefined,
        collection_status: "available",
      });
    });

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Added 2 items as "On shelf (no status)" to your collection.');
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["items"] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["works", "shelf"] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["expressions", "shelf"] }));
      expect(onClearSelection).toHaveBeenCalled();
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
