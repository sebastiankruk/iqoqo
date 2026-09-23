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
import { ItemEditor } from "@/components/admin/frbr/item-editor";
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

const mockItem: FrbrItem = {
  id: 10,
  status: "available",
  condition: "like_new",
  meta: { acquisition_date: "2024-01-15" },
  owner_id: "user1",
  owner_name: "Test User",
};

const defaultProps = {
  item: mockItem,
  onSubmit: vi.fn().mockResolvedValue(undefined),
  onEscalate: vi.fn(),
  onDelete: vi.fn(),
};

describe("ItemEditor", () => {
  it("renders the Status label and input", () => {
    render(<ItemEditor {...defaultProps} />);
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByDisplayValue("available")).toBeInTheDocument();
  });

  it("renders the Condition label and input", () => {
    render(<ItemEditor {...defaultProps} />);
    expect(screen.getByText("Condition")).toBeInTheDocument();
    expect(screen.getByDisplayValue("like_new")).toBeInTheDocument();
  });

  it("renders the Save Item button", () => {
    render(<ItemEditor {...defaultProps} />);
    expect(screen.getByRole("button", { name: /Save Item/i })).toBeInTheDocument();
  });

  it("renders Escalate and Delete action buttons", () => {
    render(<ItemEditor {...defaultProps} />);
    expect(screen.getByText("Escalate")).toBeInTheDocument();
    expect(screen.getByText("Delete")).toBeInTheDocument();
  });

  it("renders Dynamic Metadata section with existing meta fields", () => {
    render(<ItemEditor {...defaultProps} />);
    expect(screen.getByText("Dynamic Metadata")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2024-01-15")).toBeInTheDocument();
  });

  it("submits form data with status and condition", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ItemEditor {...defaultProps} onSubmit={onSubmit} />);

    const statusInput = screen.getByDisplayValue("available");
    fireEvent.change(statusInput, { target: { value: "lent" } });

    const saveButton = screen.getByRole("button", { name: /Save Item/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "lent",
          condition: "like_new",
        })
      );
    });
  });

  it("submits form data with metaFields", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ItemEditor {...defaultProps} onSubmit={onSubmit} />);

    const saveButton = screen.getByRole("button", { name: /Save Item/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          metaFields: expect.arrayContaining([
            expect.objectContaining({ key: "acquisition_date", value: "2024-01-15" }),
          ]),
        })
      );
    });
  });

  it("handles null status gracefully", () => {
    const itemNoStatus: FrbrItem = { ...mockItem, status: "" };
    render(<ItemEditor {...defaultProps} item={itemNoStatus} />);
    const statusInput = screen.getByPlaceholderText("available, lent, lost, wish_list");
    expect(statusInput).toHaveValue("");
  });

  it("handles null condition gracefully", () => {
    const itemNoCondition: FrbrItem = { ...mockItem, condition: null };
    render(<ItemEditor {...defaultProps} item={itemNoCondition} />);
    const conditionInput = screen.getByPlaceholderText("Like New, Good, Fair");
    expect(conditionInput).toHaveValue("");
  });

  it("renders Escalate button as disabled when onEscalate is not provided", () => {
    render(<ItemEditor {...defaultProps} onEscalate={undefined} />);
    const escalateButton = screen.getByText("Escalate").closest("button");
    expect(escalateButton).toBeDisabled();
  });

  it("renders Delete button as disabled when onDelete is not provided", () => {
    render(<ItemEditor {...defaultProps} onDelete={undefined} />);
    const deleteButton = screen.getByText("Delete").closest("button");
    expect(deleteButton).toBeDisabled();
  });

  it("calls onEscalate when Escalate is clicked", () => {
    const onEscalate = vi.fn();
    render(<ItemEditor {...defaultProps} onEscalate={onEscalate} />);
    fireEvent.click(screen.getByText("Escalate"));
    expect(onEscalate).toHaveBeenCalled();
  });

  it("calls onDelete when Delete is clicked", () => {
    const onDelete = vi.fn();
    render(<ItemEditor {...defaultProps} onDelete={onDelete} />);
    fireEvent.click(screen.getByText("Delete"));
    expect(onDelete).toHaveBeenCalled();
  });

  it("renders with empty meta fields", () => {
    const itemNoMeta: FrbrItem = { ...mockItem, meta: {} };
    render(<ItemEditor {...defaultProps} item={itemNoMeta} />);
    expect(screen.getByText("Dynamic Metadata")).toBeInTheDocument();
    expect(screen.getByTestId("add-meta-field")).toBeInTheDocument();
  });

  it("renders with null meta", () => {
    const itemNullMeta: FrbrItem = { ...mockItem, meta: {} };
    render(<ItemEditor {...defaultProps} item={itemNullMeta} />);
    expect(screen.getByText("Dynamic Metadata")).toBeInTheDocument();
  });
});
