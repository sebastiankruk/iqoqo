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
import { describe, it, expect } from "vitest";
import { SidebarLendingInfo } from "@/components/item/sidebar/sidebar-lending-info";
import type { Item } from "@/types/frbr";

describe("SidebarLendingInfo Unit Test (Plain Props)", () => {
  it("renders lent to name when item is lent", () => {
    const item = {
      collection_status: "lent",
      is_borrowed: false,
      lent_to_name: "Frodo",
    } as unknown as Item;

    render(<SidebarLendingInfo item={item} />);
    expect(screen.getByText(/Lent to:/i)).toBeInTheDocument();
    expect(screen.getByText("Frodo")).toBeInTheDocument();
  });

  it("renders borrowed from name when item is borrowed", () => {
    const item = {
      collection_status: "available",
      is_borrowed: true,
      owner_name: "Samwise",
    } as unknown as Item;

    render(<SidebarLendingInfo item={item} />);
    expect(screen.getByText(/Borrowed from:/i)).toBeInTheDocument();
    expect(screen.getByText("Samwise")).toBeInTheDocument();
  });

  it("renders nothing when neither lent nor borrowed", () => {
    const item = {
      collection_status: "available",
      is_borrowed: false,
    } as unknown as Item;

    const { container } = render(<SidebarLendingInfo item={item} />);
    expect(container.firstChild).toBeNull();
  });
});
