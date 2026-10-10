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
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { ItemSidebar } from "@/components/item/item-sidebar";
import * as hooks from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useUpdateItem: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUserSearch: vi.fn(() => ({ data: [], isLoading: false })),
  useLoanStatus: vi.fn(() => ({ data: null })),
  useRequestLoan: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useProfile: vi.fn(() => ({
    data: {
      id: "owner-1",
      roles: ["admin"],
      permissions: ["upload:cover", "write:metadata"],
    },
  })),
  useItemCollections: vi.fn().mockReturnValue({ data: [], isLoading: false }),
  useAddItemToCollection: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useRemoveItemFromCollection: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  useUserCollections: vi.fn().mockReturnValue({ data: [], isLoading: false }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), replace: vi.fn(), push: vi.fn() }),
  usePathname: vi.fn().mockReturnValue("/"),
}));

const comprehensiveItem = {
  id: 42,
  manifestation_id: 101,
  owner_id: "owner-1",
  is_owner: true,
  title: "The Hobbit",
  status: "reading",
  collection_status: "lent",
  lent_to_name: "Bilbo Baggins",
  is_hidden: true,
  isbn: "978-0-395-07122-1",
  cover_url: "/static/covers/hobbit.jpg",
  cover_status: "ready",
  manifestation_meta: {
    format: "book",
    cover_source: "openlibrary",
  },
  expression: {
    content_type: "text",
    language: "eng",
  },
} as unknown as Item;

describe("ItemSidebar Baseline Suite (Task 1.1)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders cover region distinguishing elements", () => {
    render(<ItemSidebar item={comprehensiveItem} />);
    const img = screen.getByRole("img");
    expect(img.getAttribute("src")).toContain("/static/covers/hobbit.jpg");
    expect(img).toHaveAttribute("alt", "The Hobbit");
  });

  it("renders status badges region distinguishing elements", () => {
    render(<ItemSidebar item={comprehensiveItem} />);
    expect(screen.getByText("LENT OUT")).toBeInTheDocument();
    expect(screen.getByText("READING...")).toBeInTheDocument();
    expect(screen.getByText("HIDDEN")).toBeInTheDocument();
  });

  it("renders lending info region distinguishing elements", () => {
    render(<ItemSidebar item={comprehensiveItem} />);
    expect(screen.getByText(/Lent to:/i)).toBeInTheDocument();
    expect(screen.getByText("Bilbo Baggins")).toBeInTheDocument();
  });

  it("renders borrowed lending info when item is borrowed", () => {
    const borrowedItem = {
      ...comprehensiveItem,
      collection_status: "available",
      is_borrowed: true,
      owner_name: "Gandalf",
      lent_to_name: null,
    } as unknown as Item;

    render(<ItemSidebar item={borrowedItem} />);
    expect(screen.getByText(/Borrowed from:/i)).toBeInTheDocument();
    expect(screen.getByText("Gandalf")).toBeInTheDocument();
  });

  it("renders ISBN region distinguishing elements", () => {
    render(<ItemSidebar item={comprehensiveItem} />);
    expect(screen.getByText("ISBN: 978-0-395-07122-1")).toBeInTheDocument();
  });

  it("renders action buttons and status selects region distinguishing elements", () => {
    const onEdit = vi.fn();
    render(<ItemSidebar item={comprehensiveItem} onEdit={onEdit} />);
    expect(screen.getByLabelText("Collection status")).toBeInTheDocument();
    expect(screen.getByLabelText("Item status")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Edit Metadata/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Make Public/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Print QR Code/i })).toBeInTheDocument();
  });

  it("renders FRBR quick info region distinguishing elements", () => {
    render(<ItemSidebar item={comprehensiveItem} />);
    expect(screen.getByText("Format")).toBeInTheDocument();
    expect(screen.getByText("text")).toBeInTheDocument();
    expect(screen.getByText("Language")).toBeInTheDocument();
    expect(screen.getByText("eng")).toBeInTheDocument();
  });
});
