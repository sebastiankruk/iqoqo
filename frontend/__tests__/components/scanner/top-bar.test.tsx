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

/**
 * Tests for TopBar scanner component.
 *
 * Verifies format selector, policy selector, flash toggle, and back-link.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TopBar } from "@/components/scanner/top-bar";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    onClick,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    onClick?: React.MouseEventHandler;
    [key: string]: unknown;
  }) => (
    <a href={href} onClick={onClick} {...props}>
      {children}
    </a>
  ),
}));

// Mock the MEDIA_REGISTRY to provide icons
vi.mock("@/lib/media", () => ({
  MEDIA_REGISTRY: {
    book: { icon: () => null, label: "Book" },
    audiobook: { icon: () => null, label: "Audiobook" },
    music: { icon: () => null, label: "Music" },
    movie: { icon: () => null, label: "Movie" },
    board_game: { icon: () => null, label: "Board Game" },
    puzzle: { icon: () => null, label: "Puzzle" },
  },
}));

describe("TopBar", () => {
  const setFormat = vi.fn();
  const setPolicy = vi.fn();
  const onCancel = vi.fn();
  const onToggleFlash = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders format selector with all scan formats", () => {
    render(<TopBar currentFormat="book" setFormat={setFormat} currentPolicy="inventory" setPolicy={setPolicy} />);

    // Should render the "Scan New Item" title
    expect(screen.getByText("Scan New Item")).toBeInTheDocument();

    // Check format buttons exist (via aria-label)
    ["Book", "Audiobook", "Music", "Movie", "Board Game", "Puzzle"].forEach(label => {
      expect(screen.getByLabelText(label)).toBeInTheDocument();
    });
  });

  it("policy selector renders inventory/wishlist/catalog options", () => {
    render(<TopBar currentFormat="book" setFormat={setFormat} currentPolicy="inventory" setPolicy={setPolicy} />);

    expect(screen.getByText("Inventory")).toBeInTheDocument();
    expect(screen.getByText("Wishlist")).toBeInTheDocument();
    expect(screen.getByText("Catalog")).toBeInTheDocument();
  });

  it("policy change calls setPolicy callback", () => {
    render(<TopBar currentFormat="book" setFormat={setFormat} currentPolicy="inventory" setPolicy={setPolicy} />);

    fireEvent.click(screen.getByText("Wishlist"));
    expect(setPolicy).toHaveBeenCalledWith("wishlist");
  });

  it("flash toggle button renders when hasFlash is true", () => {
    render(
      <TopBar
        currentFormat="book"
        setFormat={setFormat}
        currentPolicy="inventory"
        setPolicy={setPolicy}
        hasFlash={true}
        isFlashOn={false}
        onToggleFlash={onToggleFlash}
      />
    );

    const flashBtn = screen.getByLabelText("Toggle flash");
    expect(flashBtn).toBeInTheDocument();

    fireEvent.click(flashBtn);
    expect(onToggleFlash).toHaveBeenCalled();
  });

  it("flash button hidden when hasFlash is false", () => {
    render(
      <TopBar
        currentFormat="book"
        setFormat={setFormat}
        currentPolicy="inventory"
        setPolicy={setPolicy}
        hasFlash={false}
      />
    );

    expect(screen.queryByLabelText("Toggle flash")).not.toBeInTheDocument();
  });

  it("back-link invokes cancel callback", () => {
    render(
      <TopBar
        currentFormat="book"
        setFormat={setFormat}
        currentPolicy="inventory"
        setPolicy={setPolicy}
        onCancel={onCancel}
      />
    );

    const backLink = screen.getByLabelText("Go back to library");
    fireEvent.click(backLink);
    expect(onCancel).toHaveBeenCalled();
  });
});
