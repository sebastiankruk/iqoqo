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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CollectionQuickAdd } from "@/components/collection/collection-quick-add";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/lib/api/client";

// Mock apiClient
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

describe("CollectionQuickAdd", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (onCreated = vi.fn()) =>
    render(
      <QueryClientProvider client={queryClient}>
        <CollectionQuickAdd onCollectionCreated={onCreated} />
      </QueryClientProvider>
    );

  it("renders correctly and starts with disabled submit", () => {
    renderComponent();
    const input = screen.getByPlaceholderText("New collection...");
    const button = screen.getByRole("button");

    expect(input).toBeInTheDocument();
    expect(button).toBeDisabled();
  });

  it("submits a new collection and clears input on success", async () => {
    const mockOnCreated = vi.fn();
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, collection: { id: 99, name: "Sci-Fi" } },
    });

    renderComponent(mockOnCreated);
    const input = screen.getByPlaceholderText("New collection...");
    const button = screen.getByRole("button");

    fireEvent.change(input, { target: { value: "Sci-Fi" } });
    expect(button).not.toBeDisabled();

    fireEvent.click(button);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/collections", { name: "Sci-Fi" });
    });

    await waitFor(() => {
      expect(mockOnCreated).toHaveBeenCalledWith(99);
      expect(input).toHaveValue(""); // Resets on success
    });
  });
});
