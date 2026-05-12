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
import { Hero } from "@/components/landing/hero";

describe("Hero Component", () => {
  it("renders the main heading", () => {
    render(<Hero />);
    expect(screen.getByText(/The Library of Everything/i)).toBeDefined();
  });

  it("contains functional CTAs", () => {
    render(<Hero />);
    const registerLink = screen.getByRole("link", { name: /Start Your Catalog/i });
    expect(registerLink.getAttribute("href")).toBe("/register");

    const collectionLink = screen.getByRole("link", { name: /Browse Instance/i });
    expect(collectionLink.getAttribute("href")).toBe("/collection");
  });

  it("contains a GitHub link with correct attributes", () => {
    render(<Hero />);
    const githubLink = screen.getByRole("link", { name: /GitHub/i });
    expect(githubLink.getAttribute("href")).toBe("https://github.com/sebastiankruk/iqoqo");
    expect(githubLink.getAttribute("target")).toBe("_blank");
    expect(githubLink.getAttribute("rel")).toContain("noopener");
  });
});
