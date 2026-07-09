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
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, test, expect, vi } from "vitest";
import { ItemCard } from "@/components/collection/item-card";

// Standard layout and localization mocks used across iqoqo UI tests
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

describe("iqoqo v0.7.8 ItemCard Components & Boundaries Suite", () => {
  test("renders fallback metadata cleanly without crashing when manifestation_id is null", () => {
    const looseMockItem = {
      id: 99,
      manifestation_id: null,
      manifestation: null,
      title: "Isolated Loose Manuscript",
      authors: ["Anonymous Author"],
      meta: { title: "Isolated Loose Manuscript", creator: "Anonymous Author" },
      status: "OWNED",
      updated_at: "2026-07-09T00:00:00Z",
    };

    render(<ItemCard item={looseMockItem as any} />);

    // Validates execution path did not crash out on null nested manifestation attributes
    const renderedTitles = screen.getAllByText("Isolated Loose Manuscript");
    expect(renderedTitles.length).toBeGreaterThan(0);
  });

  test("asserts that the QR Code component interface element is absent when item is virtual", () => {
    const virtualWishlistItem = {
      id: -10, // Virtual placeholder ID (< 0)
      manifestation_id: 42,
      manifestation: { title: "Target Wishlist Boardgame", cover_url: "/img.jpg" },
      title: "Target Wishlist Boardgame",
      authors: [],
      meta: {},
      status: "WISH",
      updated_at: "2026-07-09T00:00:00Z",
    };

    render(<ItemCard item={virtualWishlistItem as any} />);

    // Structural Rule: Wishlist placeholders do not represent concrete shelf specimens
    // and must never present physical inventory action hooks like QR code generation.
    const qrButton = screen.queryByRole("button", { name: /qr|code|scan/i });
    expect(qrButton).not.toBeInTheDocument();
  });
});
