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
/**
 * Tests for the CurrentContext component.
 *
 * CurrentContext fetches items filtered by "reading" and "wish_list" statuses
 * in a single request, then renders two distinct sections:
 *   - "Currently Reading" – items with status "reading"
 *   - "Wish List"         – items with status "wish_list"
 *
 * useItems is mocked so we can drive every state (loading, empty, populated)
 * without touching the network.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { Item, ItemStatus } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useItems: vi.fn(),
  useRecentManifestations: vi.fn(() => ({ data: undefined, isLoading: false, isError: false })),
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

const READING_ITEM  = makeItem(4, "reading",   "1984");
const WISH_LIST_ITEM = makeItem(5, "wish_list", "Project Hail Mary");

/** Items with statuses that should never appear in either section. */
const IRRELEVANT_ITEMS: Item[] = [
  makeItem(1, "available", "The Martian"),
  makeItem(2, "lent",      "Dune"),
  makeItem(3, "lost",      "Fahrenheit 451"),
  makeItem(6, "read",      "Brave New World"),
];

describe("CurrentContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading state ────────────────────────────────────────────────────────

  it("does not show item titles while loading", () => {
    mockUseItems.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useItems>);
    render(<CurrentContext />);
    expect(screen.queryByText("Project Hail Mary")).not.toBeInTheDocument();
    expect(screen.queryByText("1984")).not.toBeInTheDocument();
  });

  it("shows a loading skeleton section while loading", () => {
    mockUseItems.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useItems>);
    render(<CurrentContext />);
    expect(screen.getByRole("region", { name: /currently active items/i })).toBeInTheDocument();
  });

  // ── Empty state (both arrays empty) ─────────────────────────────────────

  it("is wrapped in a landmark section when both lists are empty", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    expect(screen.getByRole("region", { name: /currently active items/i })).toBeInTheDocument();
  });

  it("shows the unified empty-state message when both lists are empty", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    // The paragraph has copy that includes both the heading and the word "empty"
    expect(screen.getByText(/is empty/i)).toBeInTheDocument();
  });

  it("renders a link to /collection from the empty state", () => {
    mockUseItems.mockReturnValue(makeApiResponse([]));
    render(<CurrentContext />);
    const link = screen.getByRole("link", { name: /browse your collection/i });
    expect(link).toHaveAttribute("href", "/collection");
  });

  it("shows the empty state when only irrelevant-status items are present", () => {
    mockUseItems.mockReturnValue(makeApiResponse(IRRELEVANT_ITEMS));
    render(<CurrentContext />);
    // The empty-state paragraph is the only element containing "is empty"
    expect(screen.getByText(/is empty/i)).toBeInTheDocument();
    // None of the irrelevant items should be rendered
    for (const item of IRRELEVANT_ITEMS) {
      expect(screen.queryByText(item.title as string)).not.toBeInTheDocument();
    }
  });

  // ── "Currently Reading" section ──────────────────────────────────────────

  it("renders the 'Currently Reading' section when reading items are present", () => {
    mockUseItems.mockReturnValue(makeApiResponse([READING_ITEM]));
    render(<CurrentContext />);
    expect(screen.getByRole("region", { name: /currently reading items/i })).toBeInTheDocument();
    expect(screen.getByText("Currently Reading")).toBeInTheDocument();
  });

  it("displays reading items in the 'Currently Reading' section", () => {
    mockUseItems.mockReturnValue(makeApiResponse([READING_ITEM]));
    render(<CurrentContext />);
    expect(screen.getByText("1984")).toBeInTheDocument();
  });

  it("shows the item count badge for reading items", () => {
    mockUseItems.mockReturnValue(makeApiResponse([READING_ITEM]));
    render(<CurrentContext />);
    expect(screen.getByText("1 active")).toBeInTheDocument();
  });

  it("does not render the 'Currently Reading' section when no reading items exist", () => {
    mockUseItems.mockReturnValue(makeApiResponse([WISH_LIST_ITEM]));
    render(<CurrentContext />);
    expect(screen.queryByRole("region", { name: /currently reading items/i })).not.toBeInTheDocument();
  });

  // ── "Wish List" section ──────────────────────────────────────────────────

  it("renders the 'Wish List' section when wish_list items are present", () => {
    mockUseItems.mockReturnValue(makeApiResponse([WISH_LIST_ITEM]));
    render(<CurrentContext />);
    expect(screen.getByRole("region", { name: /wish list items/i })).toBeInTheDocument();
    expect(screen.getByText("Wish List")).toBeInTheDocument();
  });

  it("displays wish_list items in the 'Wish List' section", () => {
    mockUseItems.mockReturnValue(makeApiResponse([WISH_LIST_ITEM]));
    render(<CurrentContext />);
    expect(screen.getByText("Project Hail Mary")).toBeInTheDocument();
  });

  it("does not render the 'Wish List' section when no wish_list items exist", () => {
    mockUseItems.mockReturnValue(makeApiResponse([READING_ITEM]));
    render(<CurrentContext />);
    expect(screen.queryByRole("region", { name: /wish list items/i })).not.toBeInTheDocument();
  });

  // ── Both sections visible ────────────────────────────────────────────────

  it("renders both sections when both reading and wish_list items are present", () => {
    mockUseItems.mockReturnValue(makeApiResponse([READING_ITEM, WISH_LIST_ITEM]));
    render(<CurrentContext />);
    expect(screen.getByRole("region", { name: /currently reading items/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /wish list items/i })).toBeInTheDocument();
    expect(screen.getByText("1984")).toBeInTheDocument();
    expect(screen.getByText("Project Hail Mary")).toBeInTheDocument();
  });

  // ── Items with irrelevant statuses are never shown ───────────────────────

  it.each(IRRELEVANT_ITEMS.map((item) => [item.status, item.title as string]))(
    "never renders items with status '%s' (%s)",
    (_status, title) => {
      mockUseItems.mockReturnValue(
        makeApiResponse([READING_ITEM, WISH_LIST_ITEM, ...IRRELEVANT_ITEMS]),
      );
      render(<CurrentContext />);
      expect(screen.queryByText(title)).not.toBeInTheDocument();
    },
  );
});
