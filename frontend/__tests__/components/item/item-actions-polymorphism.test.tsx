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
import { describe, it, expect, vi, afterEach } from "vitest";
import { ItemHeader } from "@/components/item/item-header";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useWorkParts: () => ({ data: { data: [] } }),
  useUpdateItem: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: () => ({ push: vi.fn() }),
}));

const baseItem = {
  id: 1,
  owner_id: "test-user",
  is_owner: true,
  manifestation_id: 1,
  status: "available",
  meta: {},
} as unknown as Item;

describe("ItemHeader Polymorphic Primary CTA", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders logReading for a Book", () => {
    const bookItem = { ...baseItem, meta: { format: "Book" } } as unknown as Item;
    render(<ItemHeader item={bookItem} />);

    const cta = screen.getByTestId("primary-consumption-cta");
    expect(cta).toHaveTextContent(/logReading/i);
  });

  it("renders nowListening for an Audio item", () => {
    const audioItem = { ...baseItem, manifestation_meta: { format: "CD" } } as unknown as Item;
    render(<ItemHeader item={audioItem} />);

    const cta = screen.getByTestId("primary-consumption-cta");
    expect(cta).toHaveTextContent(/nowListening/i);
  });

  it("renders markAsWatched for a Video item", () => {
    const videoItem = { ...baseItem, meta: { format: "DVD" } } as unknown as Item;
    render(<ItemHeader item={videoItem} />);

    const cta = screen.getByTestId("primary-consumption-cta");
    expect(cta).toHaveTextContent(/markAsWatched/i);
  });

  it("renders logPlay for a Game", () => {
    const gameItem = { ...baseItem, meta: { format: "BoardGame" } } as unknown as Item;
    render(<ItemHeader item={gameItem} />);

    const cta = screen.getByTestId("primary-consumption-cta");
    expect(cta).toHaveTextContent(/logPlay/i);
  });

  it("omits primary consumption CTA for non-owners", () => {
    const nonOwnerItem = { ...baseItem, is_owner: false, meta: { format: "Book" } } as unknown as Item;
    render(<ItemHeader item={nonOwnerItem} />);

    expect(screen.queryByTestId("primary-consumption-cta")).not.toBeInTheDocument();
  });
});
