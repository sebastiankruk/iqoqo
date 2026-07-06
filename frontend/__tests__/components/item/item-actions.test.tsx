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
import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { ItemActions } from "@/components/item/item-actions";
import * as hooks from "@/lib/api/hooks";
import type { Item } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
  useRegenerateCover: vi.fn(() => ({ mutateAsync: vi.fn() })),
  useDeleteItem: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useUpdateItem: vi.fn(() => ({ mutate: vi.fn() })),
  queryKeys: { item: vi.fn((id: number) => ["item", id]) },
}));

const mockInvalidateQueries = vi.fn();

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: vi.fn(() => ({ setQueryData: vi.fn(), invalidateQueries: mockInvalidateQueries })),
}));

const mockItem = {
  id: 1,
  manifestation_id: 1,
  owner_id: "00000000-0000-0000-0000-000000000000",
  status: "available",
  meta: {},
  cover_status: "ready",
} as unknown as Item;

describe("ItemActions Component", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("renders no buttons if user has no permissions", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    render(<ItemActions item={mockItem} />);

    expect(screen.queryByText(/Refetch Metadata/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Regenerate Cover/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Remove from library/i)).not.toBeInTheDocument();
  });

  it("renders only permitted buttons", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: ["delete:item"] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    render(<ItemActions item={mockItem} />);

    // First click to open Admin Actions panel
    fireEvent.click(screen.getByText(/Admin Actions/i));

    expect(screen.queryByText(/Refetch Metadata/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Regenerate Cover/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Remove from library/i)).toBeInTheDocument();
  });

  it("starts polling invalidateQueries every 3s when cover_status is pending", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    const pendingItem = { ...mockItem, cover_status: "pending" } as unknown as Item;
    render(<ItemActions item={pendingItem} />);

    expect(mockInvalidateQueries).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(1);
    expect(mockInvalidateQueries).toHaveBeenCalledWith({ queryKey: ["item", pendingItem.id] });

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(2);
  });

  it("does not poll when cover_status is ready", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    render(<ItemActions item={mockItem} />);

    act(() => {
      vi.advanceTimersByTime(9000);
    });
    expect(mockInvalidateQueries).not.toHaveBeenCalled();
  });

  it("stops polling when cover_status changes from pending to ready", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    const pendingItem = { ...mockItem, cover_status: "pending" } as unknown as Item;
    const { rerender } = render(<ItemActions item={pendingItem} />);

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(1);

    // Cover becomes ready - rerender with updated prop
    rerender(<ItemActions item={mockItem} />);

    act(() => {
      vi.advanceTimersByTime(6000);
    });
    // Should remain at 1 call since polling stopped
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(1);
  });
});
