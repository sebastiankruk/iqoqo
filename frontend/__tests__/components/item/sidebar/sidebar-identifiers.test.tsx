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
import { SidebarIdentifiers } from "@/components/item/sidebar/sidebar-identifiers";

describe("SidebarIdentifiers Unit Test (Plain Props)", () => {
  it("renders ISBN when provided as string prop", () => {
    render(<SidebarIdentifiers isbn="978-0-261-10221-7" />);
    expect(screen.getByText("ISBN: 978-0-261-10221-7")).toBeInTheDocument();
  });

  it("renders nothing when isbn is null or empty", () => {
    const { container } = render(<SidebarIdentifiers isbn={null} />);
    expect(container.firstChild).toBeNull();
  });
});
