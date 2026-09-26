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
import { WorkEditor } from "@/components/admin/frbr/work-editor";
import type { FrbrTree } from "@/lib/api/admin";

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

const mockTree: FrbrTree = {
  work: { id: 1, title: "Dune", meta: { original_language: "en", genre: "science_fiction" } },
  expression: { id: 2, work_id: 1, content_type: "text", language: "en", kind: null, meta: {} },
  manifestation: {
    id: 3,
    expression_id: 2,
    isbn13: null,
    upc: null,
    ean: null,
    publisher: null,
    publication_date: null,
    meta: {},
  },
  items: [],
};

const defaultProps = {
  tree: mockTree,
  onSubmit: vi.fn().mockResolvedValue(undefined),
  onAddChild: vi.fn(),
  onEscalate: vi.fn(),
  onDelete: vi.fn(),
};

describe("WorkEditor", () => {
  it("renders the Title label and input with current value", () => {
    render(<WorkEditor {...defaultProps} />);
    expect(screen.getByText("Title")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Dune")).toBeInTheDocument();
  });

  it("renders the Save Work button", () => {
    render(<WorkEditor {...defaultProps} />);
    expect(screen.getByRole("button", { name: /Save Work/i })).toBeInTheDocument();
  });

  it("renders the Add Child button", () => {
    render(<WorkEditor {...defaultProps} />);
    expect(screen.getByRole("button", { name: /Add Child/i })).toBeInTheDocument();
  });

  it("renders Escalate and Delete action buttons", () => {
    render(<WorkEditor {...defaultProps} />);
    expect(screen.getByText("Escalate")).toBeInTheDocument();
    expect(screen.getByText("Delete")).toBeInTheDocument();
  });

  it("renders Dynamic Metadata section with existing meta fields (excluding mechanics)", () => {
    render(<WorkEditor {...defaultProps} />);
    expect(screen.getByText("Dynamic Metadata")).toBeInTheDocument();
    // Should show original_language and genre but not mechanics
    expect(screen.getByDisplayValue("en")).toBeInTheDocument();
    expect(screen.getByDisplayValue("science_fiction")).toBeInTheDocument();
  });

  it("filters out mechanics from meta fields", () => {
    const treeWithMechanics: FrbrTree = {
      ...mockTree,
      work: { id: 1, title: "Catan", meta: { mechanics: "trading,building", players: "2-4" } },
    };
    render(<WorkEditor {...defaultProps} tree={treeWithMechanics} />);
    expect(screen.getByDisplayValue("2-4")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("trading,building")).not.toBeInTheDocument();
  });

  it("submits form data with title and metaFields", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<WorkEditor {...defaultProps} onSubmit={onSubmit} />);

    const titleInput = screen.getByDisplayValue("Dune");
    fireEvent.change(titleInput, { target: { value: "Dune (Revised)" } });

    const saveButton = screen.getByRole("button", { name: /Save Work/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Dune (Revised)",
          metaFields: expect.any(Array),
        })
      );
    });
  });

  it("calls onAddChild when Add Child button is clicked", () => {
    const onAddChild = vi.fn();
    render(<WorkEditor {...defaultProps} onAddChild={onAddChild} />);
    fireEvent.click(screen.getByRole("button", { name: /Add Child/i }));
    expect(onAddChild).toHaveBeenCalled();
  });

  it("disables Add Child button when onAddChild is not provided", () => {
    render(<WorkEditor {...defaultProps} onAddChild={undefined} />);
    const addChildButton = screen.getByRole("button", { name: /Add Child/i });
    expect(addChildButton).toBeDisabled();
  });

  it("disables Escalate button when onEscalate is not provided", () => {
    render(<WorkEditor {...defaultProps} onEscalate={undefined} />);
    const escalateButton = screen.getByText("Escalate").closest("button");
    expect(escalateButton).toBeDisabled();
  });

  it("disables Delete button when onDelete is not provided", () => {
    render(<WorkEditor {...defaultProps} onDelete={undefined} />);
    const deleteButton = screen.getByText("Delete").closest("button");
    expect(deleteButton).toBeDisabled();
  });

  it("calls onEscalate when Escalate is clicked", () => {
    const onEscalate = vi.fn();
    render(<WorkEditor {...defaultProps} onEscalate={onEscalate} />);
    fireEvent.click(screen.getByText("Escalate"));
    expect(onEscalate).toHaveBeenCalled();
  });

  it("calls onDelete when Delete is clicked", () => {
    const onDelete = vi.fn();
    render(<WorkEditor {...defaultProps} onDelete={onDelete} />);
    fireEvent.click(screen.getByText("Delete"));
    expect(onDelete).toHaveBeenCalled();
  });

  it("renders with empty title when work title is empty", () => {
    const treeEmptyTitle: FrbrTree = {
      ...mockTree,
      work: { id: 1, title: "", meta: {} },
    };
    render(<WorkEditor {...defaultProps} tree={treeEmptyTitle} />);
    // The title input should be present (it's a required field with name="title")
    const titleInput = document.querySelector('input[name="title"]') as HTMLInputElement;
    expect(titleInput).toHaveValue("");
  });

  it("renders with null work gracefully", () => {
    const treeNoWork: FrbrTree = { ...mockTree, work: null };
    render(<WorkEditor {...defaultProps} tree={treeNoWork} />);
    // Should still render the form, just with empty values
    expect(screen.getByText("Title")).toBeInTheDocument();
  });

  it("renders with empty meta", () => {
    const treeNoMeta: FrbrTree = {
      ...mockTree,
      work: { id: 1, title: "Test", meta: {} },
    };
    render(<WorkEditor {...defaultProps} tree={treeNoMeta} />);
    expect(screen.getByText("Dynamic Metadata")).toBeInTheDocument();
    expect(screen.getByTestId("add-meta-field")).toBeInTheDocument();
  });

  it("renders with null meta", () => {
    const treeNullMeta: FrbrTree = {
      ...mockTree,
      work: { id: 1, title: "Test", meta: {} },
    };
    render(<WorkEditor {...defaultProps} tree={treeNullMeta} />);
    expect(screen.getByText("Dynamic Metadata")).toBeInTheDocument();
  });
});
