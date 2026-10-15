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
import { describe, it, expect, vi } from "vitest";
import { SidebarActions } from "@/components/item/sidebar/sidebar-actions";
import type { Item } from "@/types/frbr";

vi.mock("@/components/item/taxonomy-editor", () => ({
  TaxonomyEditor: () => <div data-testid="taxonomy-editor" />,
}));

describe("SidebarActions Unit Test (Plain Props)", () => {
  const mockItem = {
    id: 10,
    manifestation_id: 20,
    status: "reading",
    collection_status: "available",
  } as unknown as Item;

  it("renders collection and status controls for item modifier", () => {
    const onEdit = vi.fn();
    render(
      <SidebarActions
        item={mockItem}
        canModifyItem={true}
        onEdit={onEdit}
        isBook={true}
        collectionStatusInfo={{ label: "On Shelf", class: "bg-emerald-50" }}
        progressStatusInfo={{ label: "Reading...", class: "bg-accent/10" }}
      />
    );

    expect(screen.getByLabelText("Collection status")).toBeInTheDocument();
    expect(screen.getByLabelText("Item status")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Edit Metadata/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Print QR Code/i })).toBeInTheDocument();
  });

  it("renders loan request action for public borrower", () => {
    const handleRequestLoan = vi.fn();
    render(
      <SidebarActions
        item={mockItem}
        canModifyItem={false}
        isOwner={false}
        profile={{ id: "user-2", roles: ["member"], permissions: [] }}
        handleRequestLoan={handleRequestLoan}
        collectionStatusInfo={{ label: "On Shelf", class: "bg-emerald-50" }}
        progressStatusInfo={{ label: "Reading...", class: "bg-accent/10" }}
      />
    );

    expect(screen.getByRole("button", { name: /Request Loan/i })).toBeInTheDocument();
  });
});
