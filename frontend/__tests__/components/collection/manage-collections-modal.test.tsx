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
import { ManageCollectionsModal } from "@/components/collection/manage-collections-modal";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/lib/api/client";

// Mock apiClient
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

describe("ManageCollectionsModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.confirm = vi.fn(() => true);

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/collections") {
        return Promise.resolve({
          data: {
            success: true,
            collections: [
              { id: 1, name: "Fantasy", parent_id: null },
              { id: 2, name: "Sci-Fi", parent_id: null },
            ],
          },
        });
      }
      return Promise.resolve({ data: { success: true } });
    });
  });

  const renderComponent = (isOpen = true) =>
    render(
      <QueryClientProvider client={queryClient}>
        <ManageCollectionsModal isOpen={isOpen} onClose={vi.fn()} />
      </QueryClientProvider>
    );

  it("renders collections from the API", async () => {
    renderComponent();

    expect(await screen.findByText("Fantasy")).toBeInTheDocument();
    expect(await screen.findByText("Sci-Fi")).toBeInTheDocument();
  });

  it("enters edit mode and allows renaming", async () => {
    renderComponent();

    const editButtons = await screen.findAllByTitle("Edit Name");
    fireEvent.click(editButtons[0]);

    const editInput = screen.getByDisplayValue("Fantasy");
    fireEvent.change(editInput, { target: { value: "High Fantasy" } });

    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: { success: true } });

    const saveButton = screen.getByText("Save");
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith("/collections/1", { name: "High Fantasy" });
    });
  });

  it("triggers deletion upon confirmation", async () => {
    renderComponent();

    const deleteButtons = await screen.findAllByTitle("Delete Collection");

    vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: { success: true } });

    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(global.confirm).toHaveBeenCalled();
      expect(apiClient.delete).toHaveBeenCalledWith("/collections/1");
    });
  });
});
