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
import { SidebarStatusBadges } from "@/components/item/sidebar/sidebar-status-badges";

describe("SidebarStatusBadges Unit Test (Plain Props)", () => {
  it("renders collection availability, progress, and hidden status badges", () => {
    render(
      <SidebarStatusBadges
        collectionStatusInfo={{ label: "On Shelf", class: "bg-emerald-50 text-emerald-700" }}
        progressStatusInfo={{ label: "Reading...", class: "bg-accent/10 text-accent" }}
        isHidden={true}
      />
    );

    expect(screen.getByText("ON SHELF")).toBeInTheDocument();
    expect(screen.getByText("READING...")).toBeInTheDocument();
    expect(screen.getByText("HIDDEN")).toBeInTheDocument();
  });

  it("does not render hidden badge when isHidden is false", () => {
    render(
      <SidebarStatusBadges
        collectionStatusInfo={{ label: "On Shelf", class: "bg-emerald-50" }}
        progressStatusInfo={{ label: "Read", class: "bg-blue-50" }}
        isHidden={false}
      />
    );

    expect(screen.queryByText("HIDDEN")).toBeNull();
  });
});
