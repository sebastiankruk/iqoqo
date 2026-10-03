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
import { PublicProfilePager } from "@/components/public/public-profile-pager";

describe("PublicProfilePager", () => {
  it("renders nothing when the collection fits on one page", () => {
    const { container } = render(
      <PublicProfilePager username="jane" currentPage={1} totalPages={1} shown={9} total={9} />
    );
    // A control with nothing to control is noise, not a feature.
    expect(container.firstChild).toBeNull();
  });

  it("links each page to its query-string route", () => {
    render(<PublicProfilePager username="jane" currentPage={2} totalPages={5} shown={24} total={100} />);

    // The first page is the bare profile URL, which is what the route reads.
    expect(screen.getByRole("link", { name: "1" })).toHaveAttribute("href", "/u/jane");
    expect(screen.getByRole("link", { name: "5" })).toHaveAttribute("href", "/u/jane?page=5");
    expect(screen.getByRole("link", { name: "2" })).toHaveAttribute("href", "/u/jane?page=2");
  });

  it("marks the current page for assistive technology", () => {
    render(<PublicProfilePager username="jane" currentPage={3} totalPages={5} shown={24} total={100} />);
    expect(screen.getByRole("link", { name: "3" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "2" })).not.toHaveAttribute("aria-current");
  });

  it("reports the visible range and total", () => {
    render(<PublicProfilePager username="jane" currentPage={2} totalPages={5} shown={24} total={100} />);
    // Page 2 at 24 per page starts at item 25 -- not 49, not 1.
    expect(screen.getByText(/Showing 25–48 of 100/)).toBeInTheDocument();
  });

  it("omits the range line when the API reported no total", () => {
    render(<PublicProfilePager username="jane" currentPage={2} totalPages={5} shown={24} />);
    expect(screen.queryByText(/Showing/)).not.toBeInTheDocument();
  });

  it("disables Previous on the first page and Next on the last", () => {
    const { rerender } = render(
      <PublicProfilePager username="jane" currentPage={1} totalPages={5} shown={24} total={100} />
    );
    expect(screen.getByRole("button", { name: "Previous page" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "Next page" })).toBeInTheDocument();

    rerender(<PublicProfilePager username="jane" currentPage={5} totalPages={5} shown={24} total={100} />);
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "Previous page" })).toBeInTheDocument();
  });

  it("elides the middle of a long range but keeps first and last reachable", () => {
    render(<PublicProfilePager username="jane" currentPage={10} totalPages={40} shown={24} total={960} />);
    // First and last are always present: a collector with hundreds of items
    // should be able to jump to the end, not click "next" forty times.
    expect(screen.getByRole("link", { name: "1" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "40" })).toBeInTheDocument();
    // But a page far outside the window is not linked.
    expect(screen.queryByRole("link", { name: "30" })).not.toBeInTheDocument();
  });

  it("shows every page without gaps for a short collection", () => {
    render(<PublicProfilePager username="jane" currentPage={1} totalPages={7} shown={24} total={150} />);
    for (const p of ["1", "2", "3", "4", "5", "6", "7"]) {
      expect(screen.getByRole("link", { name: p })).toBeInTheDocument();
    }
  });

  it("percent-encodes a username that needs it", () => {
    render(<PublicProfilePager username="a b" currentPage={2} totalPages={3} shown={24} total={60} />);
    expect(screen.getByRole("link", { name: "3" })).toHaveAttribute("href", "/u/a%20b?page=3");
  });
});
