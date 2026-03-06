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
/**
 * Tests for the Navbar component.
 *
 * next/link and next/navigation are mocked globally in vitest.setup.ts.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Navbar } from "@/components/dashboard/navbar";

describe("Navbar", () => {
  it("renders the iqoqo brand name", () => {
    render(<Navbar />);
    expect(screen.getByText("iqoqo")).toBeInTheDocument();
  });

  it("renders a search input", () => {
    render(<Navbar />);
    expect(
      screen.getByPlaceholderText("Search your collection..."),
    ).toBeInTheDocument();
  });

  it("contains a link to the Collection page", () => {
    render(<Navbar />);
    const link = screen.getByRole("link", { name: /collection/i });
    expect(link).toHaveAttribute("href", "/collection");
  });

  it("contains a link to the Scan page", () => {
    render(<Navbar />);
    const links = screen.getAllByRole("link");
    const scanLink = links.find((l) => l.getAttribute("href") === "/scan");
    expect(scanLink).toBeDefined();
  });

  it("contains a link to the home page via the brand", () => {
    render(<Navbar />);
    const homeLink = screen.getByRole("link", { name: /iqoqo/i });
    expect(homeLink).toHaveAttribute("href", "/");
  });
});
