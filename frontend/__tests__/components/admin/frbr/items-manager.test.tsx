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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ItemsManager } from "@/components/admin/frbr/items-manager";
import type { FrbrItem } from "@/lib/api/admin";

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: any) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: any) => <div>{children}</div>,
  DropdownMenuContent: ({ children }: any) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick, disabled, className }: any) => (
    <button onClick={onClick} disabled={disabled} className={className}>
      {children}
    </button>
  ),
}));

const mockItems: FrbrItem[] = [
  { id: 10, status: "available", condition: "like_new", meta: {}, owner_id: "user1", owner_name: "Alice" },
  { id: 11, status: "lent", condition: "good", meta: {}, owner_id: "user2", owner_name: "Bob" },
  { id: 12, status: "available", condition: null, meta: {}, owner_id: "user3", owner_name: "Charlie" },
];

const defaultProps = {
  items: mockItems,
  onItemSubmit: vi.fn().mockResolvedValue(undefined),
  onItemEscalate: vi.fn(),
  onItemDelete: vi.fn(),
  lastFetched: 0,
};

describe("ItemsManager", () => {
  it("renders empty state message when no items", () => {
    render(<ItemsManager {...defaultProps} items={[]} />);
    expect(screen.getByText("No items associated with this manifestation.")).toBeInTheDocument();
  });

  it("renders all items", () => {
    render(<ItemsManager {...defaultProps} />);
    expect(screen.getByText("Item #10")).toBeInTheDocument();
    expect(screen.getByText("Item #11")).toBeInTheDocument();
    expect(screen.getByText("Item #12")).toBeInTheDocument();
  });

  it("renders filter inputs", () => {
    render(<ItemsManager {...defaultProps} />);
    expect(screen.getByTestId("filter-owner")).toBeInTheDocument();
    expect(screen.getByTestId("filter-status")).toBeInTheDocument();
    expect(screen.getByTestId("filter-condition")).toBeInTheDocument();
  });

  it("renders owner names", () => {
    render(<ItemsManager {...defaultProps} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Charlie")).toBeInTheDocument();
  });

  it("renders item statuses", () => {
    render(<ItemsManager {...defaultProps} />);
    // "available" appears for items 10 and 12
    const availableElements = screen.getAllByText(/available/);
    expect(availableElements.length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/lent/).length).toBeGreaterThanOrEqual(1);
  });

  it("renders item conditions when available", () => {
    render(<ItemsManager {...defaultProps} />);
    expect(screen.getByText(/like_new/)).toBeInTheDocument();
    expect(screen.getByText(/good/)).toBeInTheDocument();
  });

  it("expands an item when clicked", async () => {
    render(<ItemsManager {...defaultProps} />);
    const expandButton = screen.getByText("Item #10").closest("button")!;
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Save Item/i })).toBeInTheDocument();
    });
  });

  it("collapses an expanded item when clicked again", async () => {
    render(<ItemsManager {...defaultProps} />);
    const expandButton = screen.getByText("Item #10").closest("button")!;

    // Expand
    fireEvent.click(expandButton);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Save Item/i })).toBeInTheDocument();
    });

    // Collapse
    fireEvent.click(expandButton);
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /Save Item/i })).not.toBeInTheDocument();
    });
  });

  it("filters items by owner name", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-owner"), { target: { value: "Alice" } });
    expect(screen.getByText("Item #10")).toBeInTheDocument();
    expect(screen.queryByText("Item #11")).not.toBeInTheDocument();
    expect(screen.queryByText("Item #12")).not.toBeInTheDocument();
  });

  it("filters items by owner ID when name doesn't match", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-owner"), { target: { value: "user2" } });
    expect(screen.queryByText("Item #10")).not.toBeInTheDocument();
    expect(screen.getByText("Item #11")).toBeInTheDocument();
  });

  it("filters items by status", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-status"), { target: { value: "lent" } });
    expect(screen.queryByText("Item #10")).not.toBeInTheDocument();
    expect(screen.getByText("Item #11")).toBeInTheDocument();
    expect(screen.queryByText("Item #12")).not.toBeInTheDocument();
  });

  it("filters items by condition", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-condition"), { target: { value: "good" } });
    expect(screen.queryByText("Item #10")).not.toBeInTheDocument();
    expect(screen.getByText("Item #11")).toBeInTheDocument();
  });

  it("combines multiple filters", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-owner"), { target: { value: "Alice" } });
    fireEvent.change(screen.getByTestId("filter-status"), { target: { value: "available" } });
    expect(screen.getByText("Item #10")).toBeInTheDocument();
    expect(screen.queryByText("Item #11")).not.toBeInTheDocument();
    expect(screen.queryByText("Item #12")).not.toBeInTheDocument();
  });

  it("shows all items when filters are cleared", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-owner"), { target: { value: "Alice" } });
    expect(screen.queryByText("Item #11")).not.toBeInTheDocument();

    fireEvent.change(screen.getByTestId("filter-owner"), { target: { value: "" } });
    expect(screen.getByText("Item #10")).toBeInTheDocument();
    expect(screen.getByText("Item #11")).toBeInTheDocument();
    expect(screen.getByText("Item #12")).toBeInTheDocument();
  });

  it("renders status filter options", () => {
    render(<ItemsManager {...defaultProps} />);
    const statusSelect = screen.getByTestId("filter-status");
    expect(screen.getByRole("option", { name: "All" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "available" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "lent" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "lost" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "wish_list" })).toBeInTheDocument();
    expect(statusSelect).toHaveValue("");
  });

  it("renders owner_id when owner_name is not available", () => {
    const itemsNoName: FrbrItem[] = [{ id: 20, status: "available", condition: null, meta: {}, owner_id: "user99" }];
    render(<ItemsManager {...defaultProps} items={itemsNoName} />);
    expect(screen.getByText("user99")).toBeInTheDocument();
  });

  it("passes onItemEscalate and onItemDelete to ItemEditor when expanded", async () => {
    const onItemEscalate = vi.fn();
    const onItemDelete = vi.fn();
    render(<ItemsManager {...defaultProps} onItemEscalate={onItemEscalate} onItemDelete={onItemDelete} />);

    const expandButton = screen.getByText("Item #10").closest("button")!;
    fireEvent.click(expandButton);

    await waitFor(() => {
      expect(screen.getByText("Escalate")).toBeInTheDocument();
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });
  });

  it("does not pass escalate/delete callbacks when not provided", async () => {
    render(<ItemsManager items={mockItems} onItemSubmit={vi.fn().mockResolvedValue(undefined)} lastFetched={0} />);

    const expandButton = screen.getByText("Item #10").closest("button")!;
    fireEvent.click(expandButton);

    await waitFor(() => {
      const escalateButton = screen.getByText("Escalate").closest("button");
      expect(escalateButton).toBeDisabled();
    });
  });

  it("owner filter is case-insensitive", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-owner"), { target: { value: "alice" } });
    expect(screen.getByText("Item #10")).toBeInTheDocument();
    expect(screen.queryByText("Item #11")).not.toBeInTheDocument();
  });

  it("condition filter is case-insensitive", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-condition"), { target: { value: "GOOD" } });
    expect(screen.getByText("Item #11")).toBeInTheDocument();
    expect(screen.queryByText("Item #10")).not.toBeInTheDocument();
  });

  it("condition filter handles items with null condition", () => {
    render(<ItemsManager {...defaultProps} />);
    fireEvent.change(screen.getByTestId("filter-condition"), { target: { value: "good" } });
    // Item #12 has null condition, should not match
    expect(screen.queryByText("Item #12")).not.toBeInTheDocument();
  });
});
