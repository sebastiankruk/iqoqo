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
import { ItemActions } from "@/components/item/item-actions";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(() => ({
    data: { id: "test-user", permissions: ["update:item"] },
  })),
  useDeleteItem: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useRegenerateCover: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useUpdateItem: vi.fn(() => ({ mutate: vi.fn() })),
  queryKeys: { item: vi.fn((id: number) => ["item", id]) },
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: vi.fn(() => ({ setQueryData: vi.fn(), invalidateQueries: vi.fn() })),
  useQuery: vi.fn(() => ({ data: [], isLoading: false })),
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/lib/api/escalations", () => ({
  useCreateEscalation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useMyEscalations: vi.fn(() => ({ data: [], isLoading: false })),
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

describe("ItemActions Polymorphism", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders Log Reading Progress for a Book", () => {
    const bookItem = { ...baseItem, meta: { format: "Book" } } as unknown as Item;
    render(<ItemActions item={bookItem} />);

    expect(screen.getByText(/Log Reading Progress/i)).toBeInTheDocument();
    expect(screen.queryByText(/Now Listening/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Now Watching/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Log Play/i)).not.toBeInTheDocument();
  });

  it("renders Now Listening for an Audio item", () => {
    const audioItem = { ...baseItem, manifestation_meta: { format: "CD" } } as unknown as Item;
    render(<ItemActions item={audioItem} />);

    expect(screen.getByText(/Now Listening/i)).toBeInTheDocument();
    expect(screen.queryByText(/Log Reading Progress/i)).not.toBeInTheDocument();
  });

  it("renders Mark as Watched for a Video item", () => {
    const videoItem = { ...baseItem, meta: { format: "DVD" } } as unknown as Item;
    render(<ItemActions item={videoItem} />);

    expect(screen.getByText(/Mark as Watched/i)).toBeInTheDocument();
    expect(screen.queryByText(/Log Reading Progress/i)).not.toBeInTheDocument();
  });

  it("renders Log Play for a Game", () => {
    const gameItem = { ...baseItem, meta: { format: "BoardGame" } } as unknown as Item;
    render(<ItemActions item={gameItem} />);

    expect(screen.getByText(/Log Play/i)).toBeInTheDocument();
    expect(screen.queryByText(/Log Reading Progress/i)).not.toBeInTheDocument();
  });
});
