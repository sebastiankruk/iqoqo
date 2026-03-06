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
import { describe, it, expect } from "vitest";
import { ItemHeader } from "@/components/item/item-header";

// Mock Item data — uses work-level fields as returned by the API
const mockItem = {
  id: 1,
  manifestation_id: 123,
  title: "Fallback Title",
  work: {
    title: "The Great Gatsby",
    authors: ["F. Scott Fitzgerald"],
  },
  manifestation_meta: {
    cover_status: "ready",
    Year: "1925",
    Pages: "180",
  },
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any;

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
    expect(screen.getByText("180 pages")).toBeInTheDocument();
  });

  it("does not render action buttons (they belong to the page)", () => {
    render(<ItemHeader item={mockItem} />);

    expect(screen.queryByText("Regenerate Cover")).not.toBeInTheDocument();
    expect(screen.queryByText("Refetch Metadata")).not.toBeInTheDocument();
  });
});
