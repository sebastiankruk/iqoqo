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
 * FRBR Virtual Item Boundary Tests for ItemSidebar.
 *
 * Enforces that the QR Code button is absent for virtual wishlist items (id < 0)
 * and present for concrete physical items (id > 0).
 *
 * The FRBR ontology rule:
 *   - Virtual items are UserWorkIntent adapters (id < 0) — no physical copy exists.
 *   - Physical items are concrete Item records (id > 0) — QR labeling is applicable.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { ItemSidebar } from "@/components/item/item-sidebar";
import type { Item } from "@/types/frbr";

// Mock all hooks and external dependencies
vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(() => ({
    data: {
      id: "owner-user-id",
      email: "owner@iqoqo.local",
      permissions: ["update:item", "write:metadata", "upload:cover"],
      roles: [],
    },
  })),
  useUpdateItem: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUserSearch: vi.fn(() => ({ data: [], isLoading: false })),
  useLoanStatus: vi.fn(() => ({ data: null })),
  useRequestLoan: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: vi.fn(() => ({ setQueryData: vi.fn(), invalidateQueries: vi.fn() })),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/components/item/qrcode-dialog", () => ({
  PrintQrCodeDialog: vi.fn(() => null),
}));

vi.mock("@/components/scanner/camera-capture", () => ({
  CameraCapture: vi.fn(() => null),
}));

vi.mock("@/components/scanner/multi-image-uploader", () => ({
  MultiImageUploader: vi.fn(() => null),
}));

vi.mock("@/components/item/taxonomy-editor", () => ({
  TaxonomyEditor: vi.fn(() => null),
}));

/**
 * Creates a mock Item with the given overrides.
 *
 * @param overrides - Partial overrides for the Item.
 * @returns A fully populated mock Item.
 */
function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: 1,
    manifestation_id: 10,
    owner_id: "owner-user-id",
    status: "want_to_read",
    collection_status: "wish_list",
    is_owner: true,
    meta: {},
    title: "Test Book",
    authors: ["Test Author"],
    ...overrides,
  } as Item;
}

describe("ItemSidebar FRBR Virtual Item Boundary", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("hides the QR Code button for virtual wishlist items (id < 0)", () => {
    // Virtual item: UserWorkIntent adapter — id < 0, no physical copy on shelf
    const virtualItem = makeItem({ id: -10, manifestation_id: undefined });
    render(<ItemSidebar item={virtualItem} />);

    // The QR Code button must not be rendered for virtual items
    expect(screen.queryByTestId("qrcode-btn")).not.toBeInTheDocument();
    expect(screen.queryByText("Print QR Code")).not.toBeInTheDocument();
  });

  it("shows the QR Code button for physical items (id > 0)", () => {
    // Physical item: concrete Item record with a positive ID
    const physicalItem = makeItem({ id: 5, manifestation_id: 10 });
    render(<ItemSidebar item={physicalItem} />);

    // The QR Code button must be present for owned physical items
    expect(screen.getByTestId("qrcode-btn")).toBeInTheDocument();
    expect(screen.getByText("Print QR Code")).toBeInTheDocument();
  });

  it("hides the QR Code button for edge case id=-1 (single virtual item)", () => {
    const virtualItem = makeItem({ id: -1, manifestation_id: undefined });
    render(<ItemSidebar item={virtualItem} />);

    expect(screen.queryByText("Print QR Code")).not.toBeInTheDocument();
  });
});
