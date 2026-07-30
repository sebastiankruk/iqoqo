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
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

// Mock API hooks
vi.mock("@/lib/api/hooks", () => ({
  useWorkParts: () => ({
    data: { data: [] },
  }),
}));

const mockItem: Item = {
  id: 1,
  owner_id: "user1",
  status: "want_to_read",
  collection_status: "available",
  title: "Test Book",
  authors: ["Test Author"],
  manifestation_id: 123,
  cover_status: "ready",
  meta: {},
  added_at: "2024-01-01",
  updated_at: "2024-01-01",
};

describe("ItemHeader", () => {
  it("renders title and authors", () => {
    render(<ItemHeader item={mockItem} />);
    expect(screen.getByText("Test Book")).toBeInTheDocument();
    expect(screen.getByText("Test Author")).toBeInTheDocument();
  });

  it("renders 'Movie' badge for format 'movie' and does not fall back to 'Book'", () => {
    const item: Item = {
      ...mockItem,
      manifestation_meta: { format: "movie" },
    };
    render(<ItemHeader item={item} />);
    expect(screen.getByText("Movie")).toBeInTheDocument();
    expect(screen.queryByText("Book")).not.toBeInTheDocument();
  });

  it("renders 'Movie' badge for format 'film' and does not fall back to 'Book'", () => {
    const item: Item = {
      ...mockItem,
      manifestation_meta: { format: "film" },
    };
    render(<ItemHeader item={item} />);
    expect(screen.getByText("Movie")).toBeInTheDocument();
    expect(screen.queryByText("Book")).not.toBeInTheDocument();
  });

  it("renders 'Movie' badge for format 'video' and does not fall back to 'Book'", () => {
    const item: Item = {
      ...mockItem,
      manifestation_meta: { format: "video" },
    };
    render(<ItemHeader item={item} />);
    expect(screen.getByText("Movie")).toBeInTheDocument();
    expect(screen.queryByText("Book")).not.toBeInTheDocument();
  });
});
