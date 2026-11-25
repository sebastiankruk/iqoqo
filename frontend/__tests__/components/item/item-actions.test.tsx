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
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, afterEach } from "vitest";
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
  useQuery: vi.fn(() => ({ data: [], isLoading: false })),
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/lib/api/escalations", () => ({
  useCreateEscalation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useMyEscalations: vi.fn(() => ({ data: [], isLoading: false })),
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
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders no buttons if user has no permissions", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    const { container } = render(<ItemActions item={mockItem} />);

    expect(container.firstChild).toBeNull();
    expect(screen.queryByText(/FRBR Hierarchy/i)).not.toBeInTheDocument();
  });

  it("hides Admin Actions and Remove from library for non-owner user accounts", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: {
        id: "other-user",
        email: "other@example.com",
        roles: ["user"],
        permissions: ["delete:item", "upload:cover"],
      },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    const nonOwnerItem = { ...mockItem, is_owner: false } as unknown as Item;
    render(<ItemActions item={nonOwnerItem} />);

    expect(screen.queryByTestId("admin-actions-menu-trigger")).not.toBeInTheDocument();
    expect(screen.queryByText(/Remove from library/i)).not.toBeInTheDocument();
  });

  it("renders only permitted buttons in labeled Admin Actions dropdown for owner", async () => {
    const user = userEvent.setup();
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: ["delete:item"] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    render(<ItemActions item={{ ...mockItem, is_owner: true }} />);

    expect(screen.queryByText(/FRBR Hierarchy/i)).not.toBeInTheDocument();
    const trigger = screen.getByTestId("admin-actions-menu-trigger");
    await user.click(trigger);

    expect(screen.queryByText(/Refetch Metadata/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Regenerate Cover/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Remove from library/i)).toBeInTheDocument();
  });

  describe("Visibility Guards", () => {
    it("renders nothing for unauthenticated user", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: undefined,
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const { container } = render(<ItemActions item={{ ...mockItem, is_owner: true }} />);
      expect(container.firstChild).toBeNull();
    });

    it("does not render admin actions for non-owner without admin permissions", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: { id: "test-id", email: "test@example.com", permissions: [] },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      const nonOwnerItem = { ...mockItem, is_owner: false, meta: { format: "book" } } as unknown as Item;
      render(<ItemActions item={nonOwnerItem} />);

      expect(screen.queryByTestId("admin-actions-menu-trigger")).not.toBeInTheDocument();
    });
  });

  describe("Edit FRBR button visibility (write:metadata)", () => {
    it("does NOT render Edit FRBR for user with read:metadata but WITHOUT write:metadata", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "test-id",
          email: "test@example.com",
          permissions: ["read:metadata"],
        },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      render(<ItemActions item={mockItem} />);

      expect(screen.queryByTestId("admin-actions-menu-trigger")).not.toBeInTheDocument();
      expect(screen.queryByText(/Edit FRBR/i)).not.toBeInTheDocument();
    });

    it("renders Edit FRBR inside Admin Actions dropdown for user with write:metadata permission", async () => {
      const user = userEvent.setup();
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "test-id",
          email: "test@example.com",
          permissions: ["write:metadata"],
        },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      render(<ItemActions item={mockItem} />);

      await user.click(screen.getByTestId("admin-actions-menu-trigger"));
      expect(screen.getByText(/Edit FRBR/i)).toBeInTheDocument();
    });

    it("renders flat inline actions without a nested Admin Actions dropdown when compact=true", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "test-id",
          email: "test@example.com",
          permissions: ["write:metadata", "delete:item"],
        },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      render(<ItemActions item={{ ...mockItem, is_owner: true }} compact={true} />);

      expect(screen.queryByTestId("admin-actions-menu-trigger")).not.toBeInTheDocument();
      expect(screen.getByTestId("admin-actions-inline-list")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Edit FRBR/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Remove from library/i })).toBeInTheDocument();
    });
  });
});
