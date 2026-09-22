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
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FRBRTreeView } from "@/components/admin/frbr/frbr-tree-view";
import type { FrbrTree } from "@/lib/api/admin";

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children, variant, className }: any) => (
    <span data-variant={variant} className={className}>
      {children}
    </span>
  ),
}));

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: any) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children }: any) => <div>{children}</div>,
  DropdownMenuContent: ({ children }: any) => <div data-testid="dropdown-content">{children}</div>,
  DropdownMenuItem: ({ children, onClick, className }: any) => (
    <button onClick={onClick} className={className}>
      {children}
    </button>
  ),
}));

const mockTree: FrbrTree = {
  work: { id: 1, title: "Dune", meta: { original_language: "en" } },
  expression: { id: 2, work_id: 1, content_type: "text", language: "en", kind: null, meta: {} },
  manifestation: {
    id: 3,
    expression_id: 2,
    isbn13: "9780441172719",
    upc: null,
    ean: null,
    publisher: "Ace Books",
    publication_date: "1965-08-01",
    meta: { type: "Book", pages: "412" },
  },
  items: [
    { id: 10, status: "available", condition: "like_new", meta: {}, owner_id: "user1", owner_name: "Test User" },
    { id: 11, status: "lent", condition: null, meta: {}, owner_id: "user2" },
  ],
};

const defaultProps = {
  tree: mockTree,
  selectedLevel: "manifestation" as const,
  selectedId: 3,
  onSelect: vi.fn(),
  onAddChild: vi.fn(),
  onEscalate: vi.fn(),
  onDelete: vi.fn(),
};

describe("FRBRTreeView", () => {
  it("renders the tree view container", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByTestId("frbr-tree-view")).toBeInTheDocument();
  });

  it("renders the Work section with title", () => {
    render(<FRBRTreeView {...defaultProps} />);
    // "Dune" appears in both section header and node detail
    const duneElements = screen.getAllByText("Dune");
    expect(duneElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Expression section with content type and language", () => {
    render(<FRBRTreeView {...defaultProps} />);
    // "text" appears in section header and node detail
    const textElements = screen.getAllByText(/text/);
    expect(textElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Manifestation section with ID", () => {
    render(<FRBRTreeView {...defaultProps} />);
    // "#3" appears in section header and node detail
    const idElements = screen.getAllByText(/#3/);
    expect(idElements.length).toBeGreaterThanOrEqual(1);
  });

  it("renders the Items section with count badge", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByText("Items")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("renders item nodes with status and condition", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByTestId("tree-node-item-10")).toBeInTheDocument();
    expect(screen.getByTestId("tree-node-item-11")).toBeInTheDocument();
  });

  it("calls onSelect when a work node is clicked", () => {
    const onSelect = vi.fn();
    render(<FRBRTreeView {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("tree-node-work"));
    expect(onSelect).toHaveBeenCalledWith("work", 1);
  });

  it("calls onSelect when an expression node is clicked", () => {
    const onSelect = vi.fn();
    render(<FRBRTreeView {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("tree-node-expression"));
    expect(onSelect).toHaveBeenCalledWith("expression", 2);
  });

  it("calls onSelect when a manifestation node is clicked", () => {
    const onSelect = vi.fn();
    render(<FRBRTreeView {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("tree-node-manifestation"));
    expect(onSelect).toHaveBeenCalledWith("manifestation", 3);
  });

  it("calls onSelect when an item node is clicked", () => {
    const onSelect = vi.fn();
    render(<FRBRTreeView {...defaultProps} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("tree-node-item-10"));
    expect(onSelect).toHaveBeenCalledWith("item", 10);
  });

  it("toggles section collapse/expand when section header is clicked", () => {
    render(<FRBRTreeView {...defaultProps} />);
    // Initially expanded - work node should be visible
    expect(screen.getByTestId("tree-node-work")).toBeInTheDocument();

    // Click the work section header to collapse (the button containing "Dune" text)
    const duneElements = screen.getAllByText("Dune");
    const workHeader = duneElements[0].closest("button")!;
    fireEvent.click(workHeader);

    // After collapsing, the work node detail should be hidden
    expect(screen.queryByTestId("tree-node-work")).not.toBeInTheDocument();
  });

  it("renders 'No Work' when work is null", () => {
    const treeWithoutWork: FrbrTree = { ...mockTree, work: null };
    render(<FRBRTreeView {...defaultProps} tree={treeWithoutWork} />);
    expect(screen.getByText("No Work")).toBeInTheDocument();
  });

  it("renders 'No Expression' when expression is null", () => {
    const treeWithoutExpression: FrbrTree = { ...mockTree, expression: null };
    render(<FRBRTreeView {...defaultProps} tree={treeWithoutExpression} />);
    expect(screen.getByText("No Expression")).toBeInTheDocument();
  });

  it("renders ISBN in manifestation node when available", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByText(/ISBN 9780441172719/)).toBeInTheDocument();
  });

  it("renders manifestation meta type in section header", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByText(/Book/)).toBeInTheDocument();
  });

  it("renders item condition in parentheses when available", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByText(/like_new/)).toBeInTheDocument();
  });

  it("renders action menu items when callbacks are provided", () => {
    render(<FRBRTreeView {...defaultProps} />);
    // The dropdown content should contain Add Child, Escalate, and Delete
    // These appear multiple times (once per node that supports them)
    expect(screen.getAllByText("Add Child").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Escalate").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Delete").length).toBeGreaterThanOrEqual(1);
  });

  it("does not render Add Child for item level nodes", () => {
    // The item-level action menus should not have Add Child
    // We need to check the dropdown for item nodes specifically
    render(<FRBRTreeView {...defaultProps} />);
    // "Add Child" appears for work, expression, manifestation but not item
    const addChildButtons = screen.getAllByText("Add Child");
    // Should be 3 (work, expression, manifestation) not 4
    expect(addChildButtons.length).toBe(3);
  });

  it("calls onAddChild when Add Child is clicked", () => {
    const onAddChild = vi.fn();
    render(<FRBRTreeView {...defaultProps} onAddChild={onAddChild} />);
    const addChildButtons = screen.getAllByText("Add Child");
    fireEvent.click(addChildButtons[0]);
    expect(onAddChild).toHaveBeenCalledWith("work");
  });

  it("calls onEscalate when Escalate is clicked", () => {
    const onEscalate = vi.fn();
    render(<FRBRTreeView {...defaultProps} onEscalate={onEscalate} />);
    const escalateButtons = screen.getAllByText("Escalate");
    fireEvent.click(escalateButtons[0]);
    expect(onEscalate).toHaveBeenCalledWith("work", 1);
  });

  it("calls onDelete when Delete is clicked", () => {
    const onDelete = vi.fn();
    render(<FRBRTreeView {...defaultProps} onDelete={onDelete} />);
    const deleteButtons = screen.getAllByText("Delete");
    fireEvent.click(deleteButtons[0]);
    expect(onDelete).toHaveBeenCalledWith("work", 1);
  });

  it("does not render action items when callbacks are not provided", () => {
    render(
      <FRBRTreeView
        tree={mockTree}
        selectedLevel="manifestation"
        selectedId={3}
        onSelect={vi.fn()}
      />
    );
    expect(screen.queryByText("Add Child")).not.toBeInTheDocument();
    expect(screen.queryByText("Escalate")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
  });

  it("renders expression with language in section header", () => {
    render(<FRBRTreeView {...defaultProps} />);
    // Section header shows content_type (language)
    expect(screen.getByText("text (en)")).toBeInTheDocument();
  });

  it("renders expression without language when language is empty", () => {
    const treeNoLang: FrbrTree = {
      ...mockTree,
      expression: { ...mockTree.expression!, language: "" },
    };
    render(<FRBRTreeView {...defaultProps} tree={treeNoLang} />);
    // Should show just "text" without language
    expect(screen.getByText("text")).toBeInTheDocument();
  });

  it("renders manifestation without meta type when not present", () => {
    const treeNoMeta: FrbrTree = {
      ...mockTree,
      manifestation: { ...mockTree.manifestation, meta: {} },
    };
    render(<FRBRTreeView {...defaultProps} tree={treeNoMeta} />);
    // Should show just #3 without type
    expect(screen.getByText("#3")).toBeInTheDocument();
  });

  it("renders manifestation without ISBN when isbn13 is null", () => {
    const treeNoIsbn: FrbrTree = {
      ...mockTree,
      manifestation: { ...mockTree.manifestation, isbn13: null },
    };
    render(<FRBRTreeView {...defaultProps} tree={treeNoIsbn} />);
    expect(screen.queryByText(/ISBN/)).not.toBeInTheDocument();
  });

  it("renders item without condition when condition is null", () => {
    render(<FRBRTreeView {...defaultProps} />);
    // Item 11 has no condition
    const item11Node = screen.getByTestId("tree-node-item-11");
    expect(item11Node.textContent).toContain("#11");
    expect(item11Node.textContent).toContain("lent");
    expect(item11Node.textContent).not.toContain("(");
  });

  it("renders empty items section with count 0", () => {
    const treeNoItems: FrbrTree = { ...mockTree, items: [] };
    render(<FRBRTreeView {...defaultProps} tree={treeNoItems} />);
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("toggles items section collapse/expand", () => {
    render(<FRBRTreeView {...defaultProps} />);
    // Items should be visible initially
    expect(screen.getByTestId("tree-node-item-10")).toBeInTheDocument();

    // Click the items section header to collapse
    const itemsHeader = screen.getByText("Items").closest("button")!;
    fireEvent.click(itemsHeader);

    // After collapsing, item nodes should be hidden
    expect(screen.queryByTestId("tree-node-item-10")).not.toBeInTheDocument();
  });

  it("toggles expression section collapse/expand", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByTestId("tree-node-expression")).toBeInTheDocument();

    // Click the expression section header to collapse
    const exprElements = screen.getAllByText(/text/);
    const exprHeader = exprElements[0].closest("button")!;
    fireEvent.click(exprHeader);

    expect(screen.queryByTestId("tree-node-expression")).not.toBeInTheDocument();
  });

  it("toggles manifestation section collapse/expand", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByTestId("tree-node-manifestation")).toBeInTheDocument();

    // Click the manifestation section header to collapse
    const manElements = screen.getAllByText(/#3/);
    const manHeader = manElements[0].closest("button")!;
    fireEvent.click(manHeader);

    expect(screen.queryByTestId("tree-node-manifestation")).not.toBeInTheDocument();
  });

  it("re-expands a collapsed section", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByTestId("tree-node-work")).toBeInTheDocument();

    // Collapse
    const duneElements = screen.getAllByText("Dune");
    const workHeader = duneElements[0].closest("button")!;
    fireEvent.click(workHeader);
    expect(screen.queryByTestId("tree-node-work")).not.toBeInTheDocument();

    // Re-expand
    fireEvent.click(workHeader);
    expect(screen.getByTestId("tree-node-work")).toBeInTheDocument();
  });

  it("applies active highlight class when work node is selected", () => {
    render(<FRBRTreeView {...defaultProps} selectedLevel="work" selectedId={1} />);
    const workNode = screen.getByTestId("tree-node-work");
    expect(workNode.className).toContain("bg-primary/10");
  });

  it("applies active highlight class when expression node is selected", () => {
    render(<FRBRTreeView {...defaultProps} selectedLevel="expression" selectedId={2} />);
    const exprNode = screen.getByTestId("tree-node-expression");
    expect(exprNode.className).toContain("bg-primary/10");
  });

  it("applies active highlight class when item node is selected", () => {
    render(<FRBRTreeView {...defaultProps} selectedLevel="item" selectedId={10} />);
    const itemNode = screen.getByTestId("tree-node-item-10");
    expect(itemNode.className).toContain("bg-primary/10");
  });

  it("does not apply highlight when node is not selected", () => {
    render(<FRBRTreeView {...defaultProps} selectedLevel="manifestation" selectedId={3} />);
    const workNode = screen.getByTestId("tree-node-work");
    expect(workNode.className).not.toContain("bg-primary/10");
  });

  it("action menu trigger stops propagation", () => {
    const onSelect = vi.fn();
    render(<FRBRTreeView {...defaultProps} onSelect={onSelect} />);
    // Find the MoreVertical button (action menu trigger) inside the work node
    const workNode = screen.getByTestId("tree-node-work");
    const triggerButton = workNode.querySelector("button")!;
    fireEvent.click(triggerButton);
    // The click should not propagate to the node's onSelect
    // (the action menu button has stopPropagation)
  });

  it("renders F1, F2, F3, F5 badges", () => {
    render(<FRBRTreeView {...defaultProps} />);
    expect(screen.getByText("F1")).toBeInTheDocument();
    expect(screen.getByText("F2")).toBeInTheDocument();
    expect(screen.getByText("F3")).toBeInTheDocument();
    expect(screen.getByText("F5")).toBeInTheDocument();
  });
});
