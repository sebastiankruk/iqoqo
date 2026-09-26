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
import { ExpressionEditor } from "@/components/admin/frbr/expression-editor";
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
  work: { id: 1, title: "Dune", meta: {} },
  expression: {
    id: 2,
    work_id: 1,
    content_type: "text",
    language: "en",
    kind: "live_performance",
    meta: { recording_venue: "Studio A" },
  },
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

describe("ExpressionEditor", () => {
  it("renders the Content Type label and select", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByText("Content Type")).toBeInTheDocument();
  });

  it("renders the Kind label and select", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByText("Kind")).toBeInTheDocument();
  });

  it("renders the Language label and input", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByText("Language")).toBeInTheDocument();
    expect(screen.getByDisplayValue("en")).toBeInTheDocument();
  });

  it("pre-selects the current content type", () => {
    render(<ExpressionEditor {...defaultProps} />);
    const contentSelect = screen.getByDisplayValue("Text (Book/Comic/Manga/Magazine)");
    expect(contentSelect).toBeInTheDocument();
  });

  it("pre-selects the current kind", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByDisplayValue("Live Performance")).toBeInTheDocument();
  });

  it("renders all content type options", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByRole("option", { name: "Text (Book/Comic/Manga/Magazine)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Image (Artwork)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Audio (Music/Audiobook/Podcast)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Video (Movie/TV Show/Anime)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Software (Video Game)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Object (Board Game/Model/Merch)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Other" })).toBeInTheDocument();
  });

  it("renders Studio / Default kind option", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByRole("option", { name: "Studio / Default" })).toBeInTheDocument();
  });

  it("renders EXPRESSION_KINDS options", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByRole("option", { name: "Live Performance" })).toBeInTheDocument();
  });

  it("renders the Save Expression button", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByRole("button", { name: /Save Expression/i })).toBeInTheDocument();
  });

  it("renders the Add Child button", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByRole("button", { name: /Add Child/i })).toBeInTheDocument();
  });

  it("renders Dynamic Metadata section", () => {
    render(<ExpressionEditor {...defaultProps} />);
    expect(screen.getByText("Dynamic Metadata")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Studio A")).toBeInTheDocument();
  });

  it("submits form data with content_type, language, kind, and metaFields", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ExpressionEditor {...defaultProps} onSubmit={onSubmit} />);

    const saveButton = screen.getByRole("button", { name: /Save Expression/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          content_type: "text",
          language: "en",
          kind: "live_performance",
          metaFields: expect.any(Array),
        })
      );
    });
  });

  it("allows changing content type", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ExpressionEditor {...defaultProps} onSubmit={onSubmit} />);

    const contentSelect = screen.getByDisplayValue("Text (Book/Comic/Manga/Magazine)");
    fireEvent.change(contentSelect, { target: { value: "audio" } });

    const saveButton = screen.getByRole("button", { name: /Save Expression/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          content_type: "audio",
        })
      );
    });
  });

  it("allows changing kind to Studio / Default", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ExpressionEditor {...defaultProps} onSubmit={onSubmit} />);

    const kindSelect = screen.getByDisplayValue("Live Performance");
    fireEvent.change(kindSelect, { target: { value: "" } });

    const saveButton = screen.getByRole("button", { name: /Save Expression/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          kind: "",
        })
      );
    });
  });

  it("allows changing language", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ExpressionEditor {...defaultProps} onSubmit={onSubmit} />);

    const langInput = screen.getByDisplayValue("en");
    fireEvent.change(langInput, { target: { value: "pl" } });

    const saveButton = screen.getByRole("button", { name: /Save Expression/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          language: "pl",
        })
      );
    });
  });

  it("calls onAddChild when Add Child button is clicked", () => {
    const onAddChild = vi.fn();
    render(<ExpressionEditor {...defaultProps} onAddChild={onAddChild} />);
    fireEvent.click(screen.getByRole("button", { name: /Add Child/i }));
    expect(onAddChild).toHaveBeenCalled();
  });

  it("disables Add Child button when onAddChild is not provided", () => {
    render(<ExpressionEditor {...defaultProps} onAddChild={undefined} />);
    const addChildButton = screen.getByRole("button", { name: /Add Child/i });
    expect(addChildButton).toBeDisabled();
  });

  it("disables Escalate button when onEscalate is not provided", () => {
    render(<ExpressionEditor {...defaultProps} onEscalate={undefined} />);
    const escalateButton = screen.getByText("Escalate").closest("button");
    expect(escalateButton).toBeDisabled();
  });

  it("disables Delete button when onDelete is not provided", () => {
    render(<ExpressionEditor {...defaultProps} onDelete={undefined} />);
    const deleteButton = screen.getByText("Delete").closest("button");
    expect(deleteButton).toBeDisabled();
  });

  it("calls onEscalate when Escalate is clicked", () => {
    const onEscalate = vi.fn();
    render(<ExpressionEditor {...defaultProps} onEscalate={onEscalate} />);
    fireEvent.click(screen.getByText("Escalate"));
    expect(onEscalate).toHaveBeenCalled();
  });

  it("calls onDelete when Delete is clicked", () => {
    const onDelete = vi.fn();
    render(<ExpressionEditor {...defaultProps} onDelete={onDelete} />);
    fireEvent.click(screen.getByText("Delete"));
    expect(onDelete).toHaveBeenCalled();
  });

  it("defaults content_type to text when expression is null", () => {
    const treeNoExpression: FrbrTree = { ...mockTree, expression: null };
    render(<ExpressionEditor {...defaultProps} tree={treeNoExpression} />);
    expect(screen.getByDisplayValue("Text (Book/Comic/Manga/Magazine)")).toBeInTheDocument();
  });

  it("defaults language to empty when expression is null", () => {
    const treeNoExpression: FrbrTree = { ...mockTree, expression: null };
    render(<ExpressionEditor {...defaultProps} tree={treeNoExpression} />);
    const langInput = screen.getByPlaceholderText("e.g., en, pl");
    expect(langInput).toHaveValue("");
  });

  it("defaults kind to empty when expression is null", () => {
    const treeNoExpression: FrbrTree = { ...mockTree, expression: null };
    render(<ExpressionEditor {...defaultProps} tree={treeNoExpression} />);
    expect(screen.getByDisplayValue("Studio / Default")).toBeInTheDocument();
  });

  it("handles expression with null kind", () => {
    const treeNullKind: FrbrTree = {
      ...mockTree,
      expression: { ...mockTree.expression!, kind: null },
    };
    render(<ExpressionEditor {...defaultProps} tree={treeNullKind} />);
    expect(screen.getByDisplayValue("Studio / Default")).toBeInTheDocument();
  });

  it("handles expression with undefined language", () => {
    const treeNoLang: FrbrTree = {
      ...mockTree,
      expression: { ...mockTree.expression!, language: "" },
    };
    render(<ExpressionEditor {...defaultProps} tree={treeNoLang} />);
    const langInput = screen.getByPlaceholderText("e.g., en, pl");
    expect(langInput).toHaveValue("");
  });
});
