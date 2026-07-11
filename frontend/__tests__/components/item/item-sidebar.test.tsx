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
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { ItemSidebar } from "@/components/item/item-sidebar";
import * as hooks from "@/lib/api/hooks";
import { useRouter } from "next/navigation";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useUpdateItem: vi.fn(),
  useUserSearch: vi.fn(() => ({ data: [], isLoading: false })),
  useLoanStatus: vi.fn(() => ({ data: null })),
  useRequestLoan: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useProfile: vi.fn(() => ({
    data: {
      permissions: ["update:item", "upload:cover", "write:metadata"],
    },
  })),
  useItemCollections: vi.fn().mockReturnValue({ data: [], isLoading: false }),
  useAddItemToCollection: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useRemoveItemFromCollection: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useUserCollections: vi.fn().mockReturnValue({ data: [], isLoading: false }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockItem = {
  id: 1,
  manifestation_id: 1,
  owner_id: "00000000-0000-0000-0000-000000000000",
  status: "unread",
  collection_status: "available",
  meta: {},
  cover_url: "/cover.jpg",
  cover_status: "ready",
  isbn: "9780544003415",
  is_owner: true,
} as unknown as Item;

describe("ItemSidebar Component", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders correctly with item data", () => {
    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useUpdateItem>);

    render(<ItemSidebar item={mockItem} />);
    // Should show both badges
    expect(screen.getAllByText(/ON SHELF/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/UNREAD/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/ISBN: 9780544003415/i)).toBeInTheDocument();
  });

  it("calls update mutation when collection status select is changed", () => {
    const mutateMock = vi.fn();
    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: mutateMock,
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useUpdateItem>);

    render(<ItemSidebar item={mockItem} />);
    const select = screen.getByLabelText("Collection status");
    fireEvent.change(select, { target: { value: "damaged" } });

    expect(mutateMock).toHaveBeenCalledTimes(1);
    expect(mutateMock).toHaveBeenCalledWith({ collection_status: "damaged" }, expect.any(Object));
  });

  it("calls update mutation when progress status select is changed", () => {
    const mutateMock = vi.fn();
    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: mutateMock,
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useUpdateItem>);

    render(<ItemSidebar item={mockItem} />);
    const select = screen.getByLabelText("Item status");
    fireEvent.change(select, { target: { value: "reading" } });

    expect(mutateMock).toHaveBeenCalledTimes(1);
    expect(mutateMock).toHaveBeenCalledWith({ status: "reading" }, expect.any(Object));
  });

  it("renders read-only status badge when owner is anonymized and no update:item permission", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: {
        permissions: [],
      },
    } as unknown as ReturnType<typeof hooks.useProfile>);
    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useUpdateItem>);

    const anonymizedItem = {
      ...mockItem,
      owner_id: "Unavailable",
      is_owner: false,
    } as unknown as Item;

    render(<ItemSidebar item={anonymizedItem} />);
    expect(screen.getAllByText(/ON SHELF/i)[0]).toBeInTheDocument();
    expect(screen.queryByLabelText("Collection status")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Item status")).not.toBeInTheDocument();
  });

  it("hides Edit Metadata button when owner is anonymized and no update:item permission", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: {
        permissions: [],
      },
    } as unknown as ReturnType<typeof hooks.useProfile>);
    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useUpdateItem>);

    const anonymizedItem = {
      ...mockItem,
      owner_id: "Unavailable",
      is_owner: false,
    } as unknown as Item;

    render(<ItemSidebar item={anonymizedItem} onEdit={vi.fn()} />);
    expect(screen.queryByText(/Edit Metadata/i)).not.toBeInTheDocument();
  });

  it("shows Edit Metadata button when owner is not anonymized", () => {
    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useUpdateItem>);

    render(<ItemSidebar item={mockItem} onEdit={vi.fn()} />);
    expect(screen.getByText(/Edit Metadata/i)).toBeInTheDocument();
  });

  it("redirects to new positive ID when virtual item is converted to physical item", () => {
    const replaceMock = vi.fn();
    vi.mocked(useRouter).mockReturnValue({
      push: vi.fn(),
      replace: replaceMock,
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      refresh: vi.fn(),
    } as unknown as ReturnType<typeof useRouter>);

    const mutateMock = vi.fn((payload, options) => {
      options.onSuccess({ success: true, data: { id: 42 } });
    });

    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: mutateMock,
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useUpdateItem>);

    const virtualItem = {
      ...mockItem,
      id: -4,
      collection_status: "wish_list",
    } as unknown as Item;

    render(<ItemSidebar item={virtualItem} />);
    const select = screen.getByLabelText("Collection status");
    fireEvent.change(select, { target: { value: "available" } });

    expect(mutateMock).toHaveBeenCalledTimes(1);
    expect(replaceMock).toHaveBeenCalledWith("/item/42");
  });

  describe("Named Collections section", () => {
    it("renders the named collections section when user owns the item", () => {
      vi.mocked(hooks.useItemCollections).mockReturnValue({
        data: [{ id: 1, name: "Favorites", parent_id: null }],
        isLoading: false,
      } as unknown as ReturnType<typeof hooks.useItemCollections>);
      vi.mocked(hooks.useUserCollections).mockReturnValue({
        data: [{ id: 2, name: "To Read", parent_id: null }],
        isLoading: false,
      } as unknown as ReturnType<typeof hooks.useUserCollections>);

      vi.mocked(hooks.useUpdateItem).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      } as unknown as ReturnType<typeof hooks.useUpdateItem>);

      render(<ItemSidebar item={mockItem} />);

      expect(screen.getByText("Named Collections")).toBeInTheDocument();
      expect(screen.getByText("Favorites")).toBeInTheDocument();
      expect(screen.getByText("Add to named collection")).toBeInTheDocument();
    });

    it("shows empty state when item has no named collections", () => {
      vi.mocked(hooks.useItemCollections).mockReturnValue({
        data: [],
        isLoading: false,
      } as unknown as ReturnType<typeof hooks.useItemCollections>);
      vi.mocked(hooks.useUserCollections).mockReturnValue({
        data: [],
        isLoading: false,
      } as unknown as ReturnType<typeof hooks.useUserCollections>);
      vi.mocked(hooks.useUpdateItem).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      } as unknown as ReturnType<typeof hooks.useUpdateItem>);

      render(<ItemSidebar item={mockItem} />);

      expect(screen.getByText("Named Collections")).toBeInTheDocument();
      expect(screen.getByText(/Not in any named collections yet/i)).toBeInTheDocument();
    });

    it("hides named collections section for virtual items (id < 0)", () => {
      const virtualItem = { ...mockItem, id: -1 };
      vi.mocked(hooks.useUpdateItem).mockReturnValue({
        mutate: vi.fn(),
        isPending: false,
      } as unknown as ReturnType<typeof hooks.useUpdateItem>);

      render(<ItemSidebar item={virtualItem} />);

      expect(screen.queryByText("Named Collections")).not.toBeInTheDocument();
    });
  });
});
