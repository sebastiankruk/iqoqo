// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { ItemSidebar } from "@/components/item/item-sidebar";
import * as hooks from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useUpdateItem: vi.fn(),
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
  status: "available",
  meta: {},
  cover_url: "/cover.jpg",
  cover_status: "ready",
  isbn: "9780544003415"
} as unknown as Item;

describe("ItemSidebar Component", () => {
  afterEach(() => { vi.clearAllMocks(); });

  it("renders correctly with item data", () => {
    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false
    } as any);

    render(<ItemSidebar item={mockItem} />);
    expect(screen.getByText(/On Shelf/i)).toBeInTheDocument();
    expect(screen.getByText(/ISBN: 9780544003415/i)).toBeInTheDocument();
  });

  it("calls update mutation when status select is changed", () => {
    const mutateMock = vi.fn();
    vi.mocked(hooks.useUpdateItem).mockReturnValue({
      mutate: mutateMock,
      isPending: false
    } as any);

    render(<ItemSidebar item={mockItem} />);
    const select = screen.getByLabelText("Item status");
    fireEvent.change(select, { target: { value: "reading" } });

    expect(mutateMock).toHaveBeenCalledTimes(1);
    expect(mutateMock).toHaveBeenCalledWith(
      { status: "reading" },
      expect.any(Object)
    );
  });
});
