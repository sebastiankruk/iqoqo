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
import * as hooks from "@/lib/api/hooks";
import type { Item } from "@/types/frbr"; // <-- Add this import

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
  useRegenerateCover: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useDeleteItem: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  queryKeys: { item: vi.fn() },
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: vi.fn(() => ({ setQueryData: vi.fn() })),
}));

const mockItem = { 
  id: 1, 
  manifestation_id: 1, 
  owner_id: "00000000-0000-0000-0000-000000000000",
  status: "available",
  meta: {},
  cover_status: 'ready' 
} as unknown as Item;

describe('ItemActions Component', () => {
  afterEach(() => { vi.clearAllMocks(); });

  it('renders no buttons if user has no permissions', () => {
    vi.mocked(hooks.useProfile).mockReturnValue({ data: { permissions: [] } });

    render(<ItemActions item={mockItem} />);

    expect(screen.queryByText(/Refetch Metadata/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Regenerate Cover/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Remove from library/i)).not.toBeInTheDocument();
  });

  it('renders only permitted buttons', () => {
    vi.mocked(hooks.useProfile).mockReturnValue({ data: { permissions: ['delete:item'] } });

    render(<ItemActions item={mockItem} />);

    expect(screen.queryByText(/Refetch Metadata/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Regenerate Cover/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Remove from library/i)).toBeInTheDocument();
  });
});
