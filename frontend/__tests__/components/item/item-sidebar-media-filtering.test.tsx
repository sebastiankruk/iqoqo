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
import { render } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { ItemSidebar } from "@/components/item/item-sidebar";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useUpdateItem: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useProfile: vi.fn(() => ({
    data: {
      permissions: ["update:item"],
    },
  })),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// Mock useRouter
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const baseItem = {
  id: 1,
  owner_id: "test-user",
  status: "available",
  meta: {},
} as unknown as Item;

describe("ItemSidebar Media Filtering", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("shows Reading Progress group for a Book", () => {
    const bookItem = { ...baseItem, meta: { format: "Book" } } as unknown as Item;
    const { container } = render(<ItemSidebar item={bookItem} />);

    expect(container.querySelector('optgroup[label="Reading Progress"]')).toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Listening Progress"]')).not.toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Watching Progress"]')).not.toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Gaming Progress"]')).not.toBeInTheDocument();
  });

  it("shows Listening Progress group for an Audio item", () => {
    const audioItem = { ...baseItem, meta: { format: "CD" } } as unknown as Item;
    const { container } = render(<ItemSidebar item={audioItem} />);

    expect(container.querySelector('optgroup[label="Listening Progress"]')).toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Reading Progress"]')).not.toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Watching Progress"]')).not.toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Gaming Progress"]')).not.toBeInTheDocument();
  });

  it("shows Watching Progress group for a Video item", () => {
    const videoItem = { ...baseItem, meta: { format: "DVD" } } as unknown as Item;
    const { container } = render(<ItemSidebar item={videoItem} />);

    expect(container.querySelector('optgroup[label="Watching Progress"]')).toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Reading Progress"]')).not.toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Listening Progress"]')).not.toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Gaming Progress"]')).not.toBeInTheDocument();
  });

  it("shows Gaming Progress group for a Game", () => {
    const gameItem = { ...baseItem, meta: { format: "BoardGame" } } as unknown as Item;
    const { container } = render(<ItemSidebar item={gameItem} />);

    expect(container.querySelector('optgroup[label="Gaming Progress"]')).toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Reading Progress"]')).not.toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Listening Progress"]')).not.toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Watching Progress"]')).not.toBeInTheDocument();
  });

  it("always shows Availability & Condition and Acquisition groups", () => {
    const { container } = render(<ItemSidebar item={baseItem} />);

    expect(container.querySelector('optgroup[label="Availability & Condition"]')).toBeInTheDocument();
    expect(container.querySelector('optgroup[label="Acquisition"]')).toBeInTheDocument();
  });
});
