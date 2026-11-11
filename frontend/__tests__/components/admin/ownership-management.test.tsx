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
import { OwnershipManagement } from "@/components/admin/ownership-management";
import * as adminApi from "@/lib/api/admin";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockGet = vi.fn();
vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: mockGet,
  }),
}));

vi.mock("@/lib/api/admin", () => ({
  getOwnershipAccounts: vi.fn(),
  getOwnershipItems: vi.fn(),
  previewOwnershipReassignment: vi.fn(),
  executeOwnershipReassignment: vi.fn(),
}));

const mockAccounts: adminApi.OwnershipAccount[] = [
  {
    id: "user-1",
    email: "alice@example.com",
    username: "alice",
    display_name: "Alice A",
    is_active: true,
  },
  {
    id: "user-2",
    email: "bob@example.com",
    username: "bob",
    display_name: "Bob B",
    is_active: true,
  },
];

const mockItems: adminApi.OwnershipSourceItem[] = [
  {
    id: 101,
    title: "Dune",
    format: "Hardcover",
    is_hidden: false,
  },
  {
    id: 102,
    title: "Neuromancer",
    format: "Paperback",
    is_hidden: false,
  },
];

describe("OwnershipManagement Component Filtering & Deep-Links", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockReturnValue(null);
    vi.mocked(adminApi.getOwnershipAccounts).mockResolvedValue(mockAccounts);
    vi.mocked(adminApi.getOwnershipItems).mockResolvedValue({
      items: mockItems,
      total: 2,
      pages: 1,
    });
  });

  it("filters items by search query and collection status", async () => {
    render(<OwnershipManagement />);

    await waitFor(() => screen.getByLabelText(/Source Account/i));

    fireEvent.change(screen.getByLabelText(/Source Account/i), {
      target: { value: "user-1" },
    });

    await waitFor(() => {
      expect(adminApi.getOwnershipItems).toHaveBeenCalledWith("user-1", 1, 20, {
        q: undefined,
        collection_status: undefined,
        item_id: undefined,
      });
    });

    const searchInput = screen.getByPlaceholderText(/Search title, ISBN, barcode/i);
    fireEvent.change(searchInput, { target: { value: "Dune" } });

    await waitFor(() => {
      expect(adminApi.getOwnershipItems).toHaveBeenCalledWith("user-1", 1, 20, {
        q: "Dune",
        collection_status: undefined,
        item_id: undefined,
      });
    });

    const statusSelect = screen.getByLabelText(/Filter by collection status/i);
    fireEvent.change(statusSelect, { target: { value: "lent" } });

    await waitFor(() => {
      expect(adminApi.getOwnershipItems).toHaveBeenCalledWith("user-1", 1, 20, {
        q: "Dune",
        collection_status: "lent",
        item_id: undefined,
      });
    });

    const clearButton = screen.getByRole("button", { name: /Clear Filters/i });
    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(adminApi.getOwnershipItems).toHaveBeenCalledWith("user-1", 1, 20, {
        q: undefined,
        collection_status: undefined,
        item_id: undefined,
      });
    });
  });

  it("hydrates sourceUserId and itemId from search params and pre-selects item", async () => {
    mockGet.mockImplementation((key: string) => {
      if (key === "sourceUserId") return "user-1";
      if (key === "itemId") return "102";
      return null;
    });

    render(<OwnershipManagement />);

    await waitFor(() => {
      expect(adminApi.getOwnershipItems).toHaveBeenCalledWith("user-1", 1, 20, {
        q: undefined,
        collection_status: undefined,
        item_id: 102,
      });
    });

    await waitFor(() => {
      const checkbox102 = screen.getByLabelText("Select item 102") as HTMLInputElement;
      expect(checkbox102.checked).toBe(true);
    });
  });
});
