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
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useUpdateItem: vi.fn(),
  useProfile: vi.fn(() => ({
    data: {
      permissions: ["update:item", "upload:cover", "write:metadata"],
    },
  })),
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
});
