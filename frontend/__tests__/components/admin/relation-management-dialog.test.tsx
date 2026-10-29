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

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RelationManagementDialog } from "@/components/admin/relation-management-dialog";
import * as adminApi from "@/lib/api/admin";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, describe, it, expect, beforeEach } from "vitest";

vi.mock("@/lib/api/admin", () => ({
  searchFrbrEntities: vi.fn(),
  reassignFrbrParent: vi.fn(),
  mergeFrbrEntities: vi.fn(),
  splitFrbrEntity: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

/**
 * Render component wrapped with QueryClientProvider for tests.
 *
 * @param ui - React element to render.
 * @returns Render result.
 */
function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("RelationManagementDialog", () => {
  const onOpenChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render dialog content when closed", () => {
    renderWithClient(
      <RelationManagementDialog
        open={false}
        onOpenChange={onOpenChange}
        entityType="manifestation"
        entityId={10}
        entityTitle="Hardcover Edition (1970)"
      />
    );

    expect(screen.queryByText(/Manage FRBR Relations/i)).not.toBeInTheDocument();
  });

  it("renders entity title and action tabs when open", () => {
    renderWithClient(
      <RelationManagementDialog
        open={true}
        onOpenChange={onOpenChange}
        entityType="manifestation"
        entityId={10}
        entityTitle="Hardcover Edition (1970)"
      />
    );

    expect(screen.getByText("Manage FRBR Relations")).toBeInTheDocument();
    expect(screen.getByText(/Manifestation: Hardcover Edition \(1970\) \(#10\)/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Reassign$/i })[0]).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Merge$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Split$/i })).toBeInTheDocument();
  });

  it("searches and reassigns to new parent entity", async () => {
    vi.mocked(adminApi.searchFrbrEntities).mockResolvedValueOnce([
      { id: 25, title: "English Translation (Walker & Co)", type: "expression" },
    ]);
    vi.mocked(adminApi.reassignFrbrParent).mockResolvedValueOnce({ id: 25 });

    renderWithClient(
      <RelationManagementDialog
        open={true}
        onOpenChange={onOpenChange}
        entityType="manifestation"
        entityId={10}
        entityTitle="Hardcover Edition (1970)"
        manifestationId={10}
      />
    );

    const searchInput = screen.getByPlaceholderText("Search for a expression...");
    fireEvent.change(searchInput, { target: { value: "English" } });

    // Press Enter to search
    fireEvent.keyDown(searchInput, { key: "Enter", code: "Enter" });

    await waitFor(() => {
      expect(adminApi.searchFrbrEntities).toHaveBeenCalledWith("English", "expression", 10);
    });

    const searchResult = await screen.findByText(/English Translation \(Walker & Co\)/i);
    fireEvent.click(searchResult);

    const submitButtons = screen.getAllByRole("button", { name: /^Reassign$/i });
    const reassignButton = submitButtons[submitButtons.length - 1];
    expect(reassignButton).not.toBeDisabled();
    fireEvent.click(reassignButton);

    await waitFor(() => {
      expect(adminApi.reassignFrbrParent).toHaveBeenCalledWith({
        entity_type: "manifestation",
        entity_id: 10,
        new_parent_id: 25,
      });
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("switches to Merge tab and merges with target entity", async () => {
    vi.mocked(adminApi.searchFrbrEntities).mockResolvedValueOnce([
      { id: 11, title: "Hardcover 2nd Printing", type: "manifestation" },
    ]);
    vi.mocked(adminApi.mergeFrbrEntities).mockResolvedValueOnce({ id: 11 });

    renderWithClient(
      <RelationManagementDialog
        open={true}
        onOpenChange={onOpenChange}
        entityType="manifestation"
        entityId={10}
        entityTitle="Hardcover Edition (1970)"
        manifestationId={10}
      />
    );

    const mergeTab = screen.getByRole("button", { name: /^Merge$/i });
    fireEvent.click(mergeTab);

    const searchInput = screen.getByPlaceholderText("Search for a manifestation to merge into...");
    fireEvent.change(searchInput, { target: { value: "Printing" } });
    fireEvent.keyDown(searchInput, { key: "Enter", code: "Enter" });

    await waitFor(() => {
      expect(adminApi.searchFrbrEntities).toHaveBeenCalledWith("Printing", "manifestation", 10);
    });

    const searchResult = await screen.findByText(/Hardcover 2nd Printing/i);
    fireEvent.click(searchResult);

    const mergeButton = screen.getByRole("button", { name: /Merge & Delete/i });
    expect(mergeButton).not.toBeDisabled();
    fireEvent.click(mergeButton);

    await waitFor(() => {
      expect(adminApi.mergeFrbrEntities).toHaveBeenCalledWith({
        entity_type: "manifestation",
        source_id: 10,
        target_id: 11,
      });
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("switches to Split tab and splits out children into new entity", async () => {
    vi.mocked(adminApi.splitFrbrEntity).mockResolvedValueOnce({ id: 99 });

    renderWithClient(
      <RelationManagementDialog
        open={true}
        onOpenChange={onOpenChange}
        entityType="work"
        entityId={5}
        entityTitle="Collected Stories"
      />
    );

    const splitTab = screen.getAllByRole("button", { name: /^Split$/i })[0];
    fireEvent.click(splitTab);

    const titleInput = screen.getByPlaceholderText("Enter title for the new entity...");
    fireEvent.change(titleInput, { target: { value: "Stand-Alone Novella" } });

    const childIdsInput = screen.getByPlaceholderText("e.g. 12, 34, 56");
    fireEvent.change(childIdsInput, { target: { value: "101, 102" } });

    const splitButtons = screen.getAllByRole("button", { name: /^Split$/i });
    const splitButton = splitButtons[splitButtons.length - 1];
    expect(splitButton).not.toBeDisabled();
    fireEvent.click(splitButton);

    await waitFor(() => {
      expect(adminApi.splitFrbrEntity).toHaveBeenCalledWith({
        entity_type: "work",
        source_id: 5,
        child_ids: [101, 102],
        new_entity_attrs: { title: "Stand-Alone Novella" },
      });
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
