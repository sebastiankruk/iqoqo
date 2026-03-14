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
import { ItemCard } from "@/components/collection/item-card";
import type { Item } from "@/types/frbr";

// Mock Next.js Image component
vi.mock("next/image", () => ({
  default: ({ src, alt, ...props }: { src: string; alt: string } & Record<string, unknown>) => {
    const rest = { ...props };
    // Remove Next.js specific props to avoid React DOM warnings in tests
    delete rest.fill;
    delete rest.sizes;
    delete rest.unoptimized;
    delete rest.priority;
    delete rest.placeholder;
    delete rest.blurDataURL;

    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...(rest as React.ComponentProps<"img">)} />;
  },
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
