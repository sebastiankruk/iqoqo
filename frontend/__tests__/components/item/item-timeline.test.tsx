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
import { render, screen, waitFor } from "@testing-library/react";
import { ItemProvenanceTimeline } from "@/components/item/item-timeline";
import { apiClient } from "@/lib/api/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

/**
 * Render component wrapped with QueryClientProvider for tests.
 *
 * @param ui - React element to render.
 * @returns Render result.
 */
function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ItemProvenanceTimeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders virtual item empty state when itemId < 0 without making API requests", () => {
    renderWithClient(<ItemProvenanceTimeline itemId={-12} />);

    expect(screen.getByTestId("virtual-item-timeline-empty")).toBeInTheDocument();
    expect(screen.getByText("No physical history")).toBeInTheDocument();
    expect(screen.getByText(/Wishlist intents do not have a physical timeline/i)).toBeInTheDocument();
    expect(apiClient.get).not.toHaveBeenCalled();
  });

  it("renders empty history state when no logs exist for physical item", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { success: true, data: [] },
    });

    renderWithClient(<ItemProvenanceTimeline itemId={42} />);

    await waitFor(() => {
      expect(screen.getByText("No history yet")).toBeInTheDocument();
    });
    expect(screen.getByText(/Status changes and collections history will appear here/i)).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith("/items/42/logs");
  });

  it("renders error state when API request fails", async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error("Network Error"));

    renderWithClient(<ItemProvenanceTimeline itemId={42} />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load item history.")).toBeInTheDocument();
    });
  });

  it("renders timeline events for creation and status progression", async () => {
    const mockLogs = [
      {
        old_status: null,
        new_status: "to_read",
        changed_at: "2026-10-25T10:00:00Z",
        log_type: "creation",
        operator_name: "Librarian",
        category: "text",
      },
      {
        old_status: "to_read",
        new_status: "in_progress",
        changed_at: "2026-10-26T12:00:00Z",
        log_type: "progress",
        operator_name: "Reader",
        category: "text",
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { success: true, data: mockLogs },
    });

    renderWithClient(<ItemProvenanceTimeline itemId={42} />);

    await waitFor(() => {
      expect(screen.getByTestId("frbr-timeline-log")).toBeInTheDocument();
    });

    expect(screen.getByText("Added to Collection")).toBeInTheDocument();
    expect(screen.getByText("Progress Updated")).toBeInTheDocument();
    expect(screen.getByText("by Librarian")).toBeInTheDocument();
    expect(screen.getByText("by Reader")).toBeInTheDocument();
    expect(screen.getByText("To Read")).toBeInTheDocument();
    expect(screen.getByText("In Progress")).toBeInTheDocument();
  });
});
