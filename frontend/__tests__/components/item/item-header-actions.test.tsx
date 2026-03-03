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
