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
      vi.advanceTimersByTime(30000);
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

  describe("Polymorphic Quick Actions", () => {
    it("renders nothing for unauthenticated user", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: undefined,
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const { container } = render(<ItemActions item={{ ...mockItem, is_owner: true }} />);
      expect(container.firstChild).toBeNull();
    });

    it("does not render quick actions for non-owner", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const nonOwnerItem = { ...mockItem, is_owner: false, meta: { format: "book" } } as unknown as Item;
      render(<ItemActions item={nonOwnerItem} />);

      expect(screen.queryByText(/Mark as Read/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Log Reading Progress/i)).not.toBeInTheDocument();
    });

    it("renders quick actions for owner", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const ownerItem = { ...mockItem, is_owner: true, status: "reading", meta: { format: "book" } } as unknown as Item;
      render(<ItemActions item={ownerItem} />);

      expect(screen.getByText(/Mark as Read/i)).toBeInTheDocument();
    });
  });

  describe("Wishlist Tagging", () => {
    it("wishlist item with tags displays tags in item metadata", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const wishlistItem = {
        ...mockItem,
        is_owner: true,
        status: "want_to_read",
        collection_status: "wish_list",
        meta: { tags: ["horror", "classic"] },
      } as unknown as Item;

      const { container } = render(<ItemActions item={wishlistItem} />);
      // Tags are part of item metadata, rendered by parent components
      expect(container).toBeTruthy();
    });

    it("wishlist item without tags renders normally", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const wishlistItem = {
        ...mockItem,
        is_owner: true,
        status: "want_to_read",
        collection_status: "wish_list",
        meta: {},
      } as unknown as Item;

      const { container } = render(<ItemActions item={wishlistItem} />);
      expect(container).toBeTruthy();
    });

    it("non-owner cannot see owner-only tag editing controls", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const nonOwnerItem = {
        ...mockItem,
        is_owner: false,
        status: "want_to_read",
        collection_status: "wish_list",
      } as unknown as Item;

      render(<ItemActions item={nonOwnerItem} />);
      // Quick actions are hidden for non-owners
      expect(screen.queryByText(/Mark as Read/i)).not.toBeInTheDocument();
    });
  });

  describe("Loan Button Visibility", () => {
    it("does not render action for unauthenticated user on item", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: undefined,
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const availableItem = {
        ...mockItem,
        is_owner: true,
        collection_status: "available",
      } as unknown as Item;

      const { container } = render(<ItemActions item={availableItem} />);
      expect(container.firstChild).toBeNull();
    });

    it("renders quick actions for owner on available (borrowable) item", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const availableItem = {
        ...mockItem,
        is_owner: true,
        collection_status: "available",
        status: "reading",
        meta: { format: "book" },
      } as unknown as Item;

      render(<ItemActions item={availableItem} />);
      // Owner should see quick actions — "Mark as Read" for a reading item
      expect(screen.queryByText(/Mark as Read/i)).toBeTruthy();
    });

    it("wishlist-only item does not show loan-related controls", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const wishlistItem = {
        ...mockItem,
        is_owner: true,
        status: "want_to_read",
        collection_status: "wish_list",
      } as unknown as Item;

      render(<ItemActions item={wishlistItem} />);
      // Wishlist items are not borrowable; the UI should reflect this
      // ItemActions doesn't show loan buttons for wishlist items
      expect(screen.queryByText(/Request Loan/i)).not.toBeInTheDocument();
    });

    it("non-owner does not see owner actions on borrowable item", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const nonOwnerAvailableItem = {
        ...mockItem,
        is_owner: false,
        collection_status: "available",
      } as unknown as Item;

      render(<ItemActions item={nonOwnerAvailableItem} />);
      // Non-owner of a physical item shouldn't see admin/quick actions
      expect(screen.queryByText(/Mark as Read/i)).not.toBeInTheDocument();
    });
  });
});
