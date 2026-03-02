import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ItemHeader } from "@/components/item/item-header";
import type { Item } from "@/types/frbr";

const mockItem: Item = {
  id: 1,
  owner_id: "user1",
  status: "available",
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
});
