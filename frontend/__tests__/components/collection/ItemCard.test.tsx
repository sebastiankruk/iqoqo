import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ItemCard } from "@/components/collection/item-card";
import type { Item } from "@/types/frbr";

// Mock Next.js Image component
vi.mock("next/image", () => ({
  default: (props: React.ComponentProps<"img">) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img {...props} alt={props.alt} />
  ),
}));

const mockItem: Item = {
  id: 1,
  owner_id: "user1",
  status: "available",
  title: "Test Book",
  authors: ["Test Author"],
  manifestation_id: 100,
  manifestation_meta: {
    cover_source: "external",
  },
  meta: {},
  added_at: "2024-01-01",
  updated_at: "2024-01-01",
};

describe("ItemCard", () => {
  it("renders the cover image when available", () => {
    const itemWithCover = {
      ...mockItem,
      cover_path: "/static/covers/test.jpg",
      cover_status: "ready",
    };

    render(<ItemCard item={itemWithCover} />);

    const img = screen.getByAltText("Cover of Test Book");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", expect.stringContaining("/static/covers/test.jpg"));
  });

  it("shows loading overlay when status is pending", () => {
    const pendingItem = {
      ...mockItem,
      cover_path: "/static/covers/placeholder.jpg",
      cover_status: "pending",
    };

    render(<ItemCard item={pendingItem} />);

    expect(screen.getByText("Generating...")).toBeInTheDocument();
  });

  it("shows processing overlay when status is processing", () => {
    const processingItem = {
      ...mockItem,
      cover_path: "/static/covers/placeholder.jpg",
      cover_status: "processing",
    };

    render(<ItemCard item={processingItem} />);

    expect(screen.getByText("Processing...")).toBeInTheDocument();
  });
});
