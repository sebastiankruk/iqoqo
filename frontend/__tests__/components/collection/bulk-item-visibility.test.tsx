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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BulkItemVisibilityToolbar } from "@/components/collection/bulk-item-visibility-toolbar";
import { chipLabel } from "@/components/collection/filter-bar";
import { buildCollectionUrl, parseCollectionUrl } from "@/lib/collection-url";
import { apiClient } from "@/lib/api/client";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) =>
    params?.count !== undefined ? `${key}:${params.count}` : key,
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    patch: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

/**
 * Render a component wrapped with a fresh non-retrying QueryClientProvider.
 *
 * @param ui - React element to render.
 * @returns Testing Library render result.
 */
function renderWithQueryClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("C128 Collection Visibility Filter & Bulk Visibility Toolbar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("round-trips visibility filter through collection URL and chipLabel", () => {
    const filters = parseCollectionUrl("visibility=friends_only,private");
    expect(filters).toEqual([
      { type: "visibility", value: "friends_only" },
      { type: "visibility", value: "private" },
    ]);
    expect(chipLabel(filters[0])).toBe("Visibility: Friends Only");
    expect(chipLabel(filters[1])).toBe("Visibility: Private / Hidden");

    const qs = buildCollectionUrl({
      sortBy: "updated",
      activeFilters: filters,
      appliedQuery: "",
      viewMode: "items",
      missingCoverOnly: false,
      missingIdOnly: false,
    });
    expect(qs).toContain("visibility=friends_only%2Cprivate");
  });

  it("renders nothing when no items are selected", () => {
    const { container } = renderWithQueryClient(
      <BulkItemVisibilityToolbar selectedItemIds={[]} onClearSelection={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("submits PATCH /items/bulk-visibility for selected items and clears on success", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({
      data: { success: true, data: { updated_count: 2, visibility: "friends_only", item_ids: [11, 22] } },
    });
    const onClear = vi.fn();
    const onSuccess = vi.fn();

    renderWithQueryClient(
      <BulkItemVisibilityToolbar selectedItemIds={[11, 22]} onClearSelection={onClear} onSuccess={onSuccess} />
    );

    expect(screen.getByTestId("bulk-item-visibility-toolbar")).toHaveTextContent("bulkVisibilitySelected:2");
    fireEvent.click(screen.getByTestId("bulk-visibility-trigger"));
    fireEvent.click(screen.getByRole("menuitem", { name: "visibilityFriendsOnly" }));

    await waitFor(() => {
      expect(apiClient.patch).toHaveBeenCalledWith("/items/bulk-visibility", {
        item_ids: [11, 22],
        visibility: "friends_only",
      });
    });
    expect(onSuccess).toHaveBeenCalled();
  });
});
