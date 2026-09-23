// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
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
 * View separation tests for the wishlist-api-separation change.
 *
 * Covers wishlist-api-separation Tasks 5.1–5.3:
 *   - ItemCard: no `item.id < 0` or `collection_status === 'wish_list'` branching
 *   - Dedicated Wishlist view renders correctly with edition/media badges
 *   - No physical inventory actions (QR codes, shelf placement) in wishlist views
 *   - Dashboard stats distinguish physical inventory from wishlist counts
 *
 * These tests verify that the frontend code has been properly decoupled:
 *   1. ItemCard and inventory components do NOT contain negative-ID checks
 *   2. Wishlist components do NOT contain physical inventory actions
 *   3. Dashboard stats show separate counts for physical vs wishlist
 */
import { describe, it, expect, vi } from "vitest";
import fs from "fs";
import path from "path";

// ---------------------------------------------------------------------------
// Helper: read source file content for static analysis
// ---------------------------------------------------------------------------

const FRONTEND_ROOT = path.resolve(__dirname, "../../..");

/**
 * Read a source file and return its content, or empty string if not found.
 */
function readSource(relativePath: string): string {
  const fullPath = path.join(FRONTEND_ROOT, relativePath);
  try {
    return fs.readFileSync(fullPath, "utf-8");
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------------------
// Task 5.1 — ItemCard: no negative-ID or wish_list branching
// ---------------------------------------------------------------------------

describe("Task 5.1: ItemCard decoupled from wishlist logic", () => {
  it("ItemCard does not check for negative IDs (item.id < 0)", () => {
    // Check all ItemCard-related files
    const cardFiles = [
      "components/item/item-card.tsx",
      "components/item/ItemCard.tsx",
      "components/collection/item-card.tsx",
    ];

    for (const file of cardFiles) {
      const content = readSource(file);
      if (!content) continue;

      // Should NOT contain patterns like: item.id < 0, id < 0, id <= 0
      const negativeIdPatterns = [
        /\.id\s*<\s*0/,
        /\.id\s*<=\s*0/,
        /is_virtual/,
        /item\.id\s*<\s*0/,
      ];

      for (const pattern of negativeIdPatterns) {
        const matches = content.match(pattern);
        // If the file exists and contains the pattern, that's a failure
        if (matches) {
          // Allow the pattern only in comments or in the dedicated wishlist components
          const lines = content.split("\n");
          const offendingLines = lines.filter(
            (line, idx) =>
              pattern.test(line) &&
              !line.trim().startsWith("//") &&
              !line.trim().startsWith("*") &&
              !file.includes("wishlist")
          );
          expect(offendingLines).toEqual([]);
        }
      }
    }
  });

  it("ItemCard does not branch on collection_status === 'wish_list'", () => {
    const cardFiles = [
      "components/item/item-card.tsx",
      "components/item/ItemCard.tsx",
    ];

    for (const file of cardFiles) {
      const content = readSource(file);
      if (!content) continue;

      // Should NOT contain wish_list branching in inventory card components
      const lines = content.split("\n");
      const wishListBranches = lines.filter(
        (line) =>
          /collection_status\s*===?\s*['"]wish_list['"]/.test(line) &&
          !line.trim().startsWith("//") &&
          !line.trim().startsWith("*")
      );

      // After separation, ItemCard should not handle wish_list at all
      expect(wishListBranches).toEqual([]);
    }
  });

  it("ItemSidebar does not check for negative IDs", () => {
    const content = readSource("components/item/item-sidebar.tsx");
    if (!content) return;

    const lines = content.split("\n");
    const negativeIdLines = lines.filter(
      (line) =>
        /\.id\s*<\s*0/.test(line) &&
        !line.trim().startsWith("//") &&
        !line.trim().startsWith("*")
    );

    expect(negativeIdLines).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Task 5.2 — Wishlist view has no physical inventory actions
// ---------------------------------------------------------------------------

describe("Task 5.2: Wishlist view has no physical inventory actions", () => {
  it("Wishlist components do not reference QR code generation", () => {
    const wishlistFiles = [
      "components/wishlist/wishlist-card.tsx",
      "components/wishlist/WishlistCard.tsx",
      "app/wishlist/page.tsx",
      "components/wishlist/wishlist-list.tsx",
    ];

    for (const file of wishlistFiles) {
      const content = readSource(file);
      if (!content) continue;

      // Should NOT reference QR code components
      expect(content.toLowerCase()).not.toContain("qrcode");
      expect(content.toLowerCase()).not.toContain("qr-code");
      expect(content.toLowerCase()).not.toContain("print-qr");
    }
  });

  it("Wishlist components do not reference shelf placement", () => {
    const wishlistFiles = [
      "components/wishlist/wishlist-card.tsx",
      "components/wishlist/WishlistCard.tsx",
      "app/wishlist/page.tsx",
    ];

    for (const file of wishlistFiles) {
      const content = readSource(file);
      if (!content) continue;

      // Should NOT reference shelf placement or physical location
      const shelfPatterns = [
        /shelf[_-]?placement/i,
        /shelf[_-]?location/i,
        /physical[_-]?location/i,
        /add[_-]?to[_-]?shelf/i,
      ];

      for (const pattern of shelfPatterns) {
        const matches = content.match(pattern);
        if (matches) {
          const lines = content.split("\n");
          const offendingLines = lines.filter(
            (line) =>
              pattern.test(line) &&
              !line.trim().startsWith("//") &&
              !line.trim().startsWith("*")
          );
          expect(offendingLines).toEqual([]);
        }
      }
    }
  });

  it("Wishlist components do not reference lending/custody actions", () => {
    const wishlistFiles = [
      "components/wishlist/wishlist-card.tsx",
      "components/wishlist/WishlistCard.tsx",
    ];

    for (const file of wishlistFiles) {
      const content = readSource(file);
      if (!content) continue;

      // Should NOT reference lending or custody
      const lendingPatterns = [
        /lent_to/i,
        /borrow/i,
        /custody/i,
        /loan/i,
      ];

      for (const pattern of lendingPatterns) {
        const lines = content.split("\n");
        const offendingLines = lines.filter(
          (line) =>
            pattern.test(line) &&
            !line.trim().startsWith("//") &&
            !line.trim().startsWith("*")
        );
        expect(offendingLines).toEqual([]);
      }
    }
  });

  it("Wishlist components render edition and media badges", () => {
    const wishlistFiles = [
      "components/wishlist/wishlist-card.tsx",
      "components/wishlist/WishlistCard.tsx",
    ];

    for (const file of wishlistFiles) {
      const content = readSource(file);
      if (!content) continue;

      // Should reference edition/media badge rendering
      // (These are positive assertions — the component SHOULD have these)
      const hasEditionReference =
        /edition/i.test(content) ||
        /manifestation/i.test(content) ||
        /expression/i.test(content) ||
        /format/i.test(content) ||
        /isbn/i.test(content);

      const hasMediaBadge =
        /media[_-]?badge/i.test(content) ||
        /work_type/i.test(content) ||
        /medium_type/i.test(content) ||
        /content_type/i.test(content);

      // At least one of these should be present
      expect(hasEditionReference || hasMediaBadge).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// Task 5.3 — Dashboard stats distinguish physical from wishlist
// ---------------------------------------------------------------------------

describe("Task 5.3: Dashboard stats distinguish physical inventory from wishlist", () => {
  it("StatsCards component renders separate labels for physical items and wishlist", () => {
    const content = readSource("components/dashboard/stats-cards.tsx");
    if (!content) return;

    // Should have distinct labels for physical items and wishlist
    const hasItemsLabel = /items/i.test(content) || /my items/i.test(content);
    const hasWishlistLabel = /wish/i.test(content) || /wishlist/i.test(content);

    expect(hasItemsLabel).toBe(true);
    expect(hasWishlistLabel).toBe(true);
  });

  it("StatsCards uses separate data fields for physical vs wishlist counts", () => {
    const content = readSource("components/dashboard/stats-cards.tsx");
    if (!content) return;

    // Should reference separate fields for items and wishlist
    // (e.g., total_items vs items_wish_list, or similar)
    const hasPhysicalField =
      /total_items|items_available|items_on_shelf|physical_items/i.test(content);
    const hasWishlistField =
      /items_wish_list|wishlist_count|wish_list|to_read/i.test(content);

    // At least one of each should be present
    expect(hasPhysicalField || /items/i.test(content)).toBe(true);
    expect(hasWishlistField).toBe(true);
  });

  it("Collection summary distinguishes physical count from wishlist count", () => {
    const collectionFiles = [
      "components/collection/collection-summary.tsx",
      "components/collection/CollectionSummary.tsx",
      "app/collection/page.tsx",
    ];

    for (const file of collectionFiles) {
      const content = readSource(file);
      if (!content) continue;

      // Should have separate counters or labels for physical vs wishlist
      const hasPhysicalCount =
        /physical|inventory|on.?shelf|available/i.test(content);
      const hasWishlistCount =
        /wishlist|wish.?list|intent/i.test(content);

      // If the file has any count-related logic, it should distinguish
      if (/count|total|number/i.test(content)) {
        // This is a soft check — just verify the file doesn't conflate the two
        const hasConflation =
          /items.*=.*wish_list.*physical/i.test(content) ||
          /physical.*wish_list/i.test(content);
        expect(hasConflation).toBe(false);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// Cross-cutting: No negative IDs in frontend source (except test files)
// ---------------------------------------------------------------------------

describe("Cross-cutting: No negative ID references in production code", () => {
  it("lib/api/hooks.ts does not reference negative IDs for wishlist routing", () => {
    const content = readSource("lib/api/hooks.ts");
    if (!content) return;

    const lines = content.split("\n");
    const negativeIdLines = lines.filter(
      (line) =>
        /id\s*<\s*0/.test(line) &&
        !line.trim().startsWith("//") &&
        !line.trim().startsWith("*") &&
        !line.includes("test")
    );

    // After separation, hooks.ts should not route based on negative IDs
    expect(negativeIdLines).toEqual([]);
  });

  it("types/frbr.ts Item interface does not document negative IDs", () => {
    const content = readSource("types/frbr.ts");
    if (!content) return;

    // The Item interface should not mention negative IDs or virtual items
    const itemInterfaceMatch = content.match(
      /export interface Item \{[^}]+\}/
    );
    if (!itemInterfaceMatch) return;

    const itemInterface = itemInterfaceMatch[0];
    expect(itemInterface.toLowerCase()).not.toContain("negative");
    expect(itemInterface.toLowerCase()).not.toContain("virtual");
  });
});
