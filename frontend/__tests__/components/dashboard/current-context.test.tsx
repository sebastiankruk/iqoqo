/**
 * Tests for the CurrentContext component.
 *
 * useItems is mocked to test loading, empty, and populated wish-list states.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { Item, ItemStatus } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useItems: vi.fn(),
}));

import { useItems } from "@/lib/api/hooks";
import { CurrentContext } from "@/components/dashboard/current-context";

const mockUseItems = vi.mocked(useItems);

function makeApiResponse(items: Item[]) {
  return {
    data: { success: true, data: items, error: null, meta: { page: 1, limit: 10, total: items.length, pages: 1 } },
    isLoading: false,
    isError: false,
  } as ReturnType<typeof useItems>;
}

function makeItem(id: number, status: ItemStatus, title: string): Item {
  return {
    id,
    manifestation_id: id,
    owner_id: "u1",
    status,
    meta: {},
    title,
    authors: ["Test Author"],
  };
}

const WISH_LIST_ITEM = makeItem(5, "wish_list", "Project Hail Mary");

/** One item per non-wish_list status — none should appear in the To Read list. */
const NON_WISH_LIST_ITEMS: Item[] = [
  makeItem(1, "available", "The Martian"),
  makeItem(2, "lent",      "Dune"),
  makeItem(3, "lost",      "Fahrenheit 451"),
  makeItem(4, "reading",   "1984"),
  makeItem(6, "read",      "Brave New World"),
];

describe("CurrentContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the 'To Read' heading", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    expect(screen.getByText("To Read")).toBeInTheDocument();
  });

  it("is wrapped in a landmark section for accessibility", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    expect(screen.getByRole("region", { name: /currently active items/i })).toBeInTheDocument();
  });

  it("shows an empty state message when there are no wish_list items", () => {
    mockUseItems.mockReturnValue(makeApiResponse([NON_WISH_LIST_ITEMS[0]]));
    render(<CurrentContext />);
    expect(screen.getByText(/to read.*list is empty/i)).toBeInTheDocument();
  });

  it("shows the empty state when all non-wish_list statuses are present but no wish_list", () => {
    mockUseItems.mockReturnValue(makeApiResponse(NON_WISH_LIST_ITEMS));
    render(<CurrentContext />);
    expect(screen.getByText(/to read.*list is empty/i)).toBeInTheDocument();
  });

  it("renders a link to /collection from the empty state", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    const link = screen.getByRole("link", { name: /browse your collection/i });
    expect(link).toHaveAttribute("href", "/collection");
  });

  it("does not show item titles while loading", () => {
    mockUseItems.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useItems>);
    render(<CurrentContext />);
    expect(screen.queryByText("Project Hail Mary")).not.toBeInTheDocument();
  });

  it("displays wish_list items when present", () => {
    mockUseItems.mockReturnValue(
      makeApiResponse([WISH_LIST_ITEM, ...NON_WISH_LIST_ITEMS]),
    );
    render(<CurrentContext />);
    expect(screen.getByText("Project Hail Mary")).toBeInTheDocument();
  });

  it.each(NON_WISH_LIST_ITEMS.map((item) => [item.status, item.title as string]))(
    "filters out items with status '%s'",
    (_status, title) => {
      mockUseItems.mockReturnValue(
        makeApiResponse([WISH_LIST_ITEM, ...NON_WISH_LIST_ITEMS]),
      );
      render(<CurrentContext />);
      expect(screen.queryByText(title)).not.toBeInTheDocument();
    },
  );
});
