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
import { describe, it, expect, vi } from "vitest";
import { ItemHeader } from "@/components/item/item-header";
import type { Item } from "@/types/frbr";

// Mock sub-components to avoid complex context requirements
vi.mock("@/components/item/item-actions", () => ({
  ItemActions: () => <div data-testid="item-actions" />,
}));

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

// Mock Item data — uses work-level fields as returned by the API
const mockItem: Item = {
  id: 1,
  owner_id: "user1",
  status: "unread",
  collection_status: "available",
  manifestation_id: 123,
  title: "Fallback Title",
  work: {
    id: 1,
    title: "The Great Gatsby",
    authors: ["F. Scott Fitzgerald"],
    meta: {},
  },
  manifestation_meta: {
    cover_status: "ready",
    Year: "1925",
    Pages: "180",
  },
  meta: {},
  added_at: "2024-01-01",
  updated_at: "2024-01-01",
};

/**
 * ItemHeader renders title/authors/year/pages from the item.
 * Action buttons (Regenerate Cover, Refetch Metadata) live in the page
 * component (app/item/[id]/page.tsx) and are tested separately.
 */
describe("ItemHeader", () => {
  it("renders item information correctly", () => {
    render(<ItemHeader item={mockItem} />);

    expect(screen.getByText("The Great Gatsby")).toBeInTheDocument();
    expect(screen.getByText("F. Scott Fitzgerald")).toBeInTheDocument();
    expect(screen.getByText("1925")).toBeInTheDocument();
    expect(screen.getByText("180")).toBeInTheDocument();
  });

  it("does not render action buttons (they belong to the page)", () => {
    render(<ItemHeader item={mockItem} />);

    expect(screen.queryByText("Regenerate Cover")).not.toBeInTheDocument();
    expect(screen.queryByText("Refetch Metadata")).not.toBeInTheDocument();
  });
});
