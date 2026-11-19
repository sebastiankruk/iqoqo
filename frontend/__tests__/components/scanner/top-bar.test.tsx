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
 * Tests for TopBar compact scanner component (C134).
 *
 * Verifies single-line Format selector dropdown, Policy selector dropdown,
 * rightAccessory slot (Batch toggle), flash toggle, and back-link.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TopBar } from "@/components/scanner/top-bar";

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

vi.mock("@/lib/media", () => ({
  MEDIA_REGISTRY: {
    book: { icon: () => null, label: "Book" },
    magazine: { icon: () => null, label: "Magazine" },
    audiobook: { icon: () => null, label: "Audiobook" },
    music: { icon: () => null, label: "Music" },
    movie: { icon: () => null, label: "Movie" },
    board_game: { icon: () => null, label: "Board Game" },
    puzzle: { icon: () => null, label: "Puzzle" },
    lego: { icon: () => null, label: "LEGO Sets" },
  },
}));

describe("TopBar", () => {
  const setFormat = vi.fn();
  const onCancel = vi.fn();
  const onToggleFlash = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders compact Format and Policy dropdown triggers on one line alongside rightAccessory", async () => {
    const user = userEvent.setup();
    render(
      <TopBar
        currentFormat="book"
        setFormat={setFormat}
        currentPolicy="inventory"
        setPolicy={vi.fn()}
        rightAccessory={<button data-testid="batch-accessory">Batch OFF</button>}
      />
    );

    expect(screen.getByText("Scan New Item")).toBeInTheDocument();
    const formatTrigger = screen.getByTestId("format-selector-trigger");
    const policyTrigger = screen.getByTestId("policy-selector-trigger");
    expect(formatTrigger).toHaveTextContent("Book");
    expect(policyTrigger).toHaveTextContent("Shelf");
    expect(screen.getByTestId("batch-accessory")).toBeInTheDocument();

    await user.click(formatTrigger);
    expect(screen.getByTestId("format-option-magazine")).toBeInTheDocument();
    expect(screen.getByTestId("format-option-lego")).toBeInTheDocument();

    await user.click(screen.getByTestId("format-option-magazine"));
    expect(setFormat).toHaveBeenCalledWith("magazine");
  });

  it("opens Policy selector menu and switches between Shelf, Wishlist, and Catalog Only", async () => {
    const user = userEvent.setup();
    const setPolicy = vi.fn();
    render(<TopBar currentFormat="book" setFormat={setFormat} currentPolicy="inventory" setPolicy={setPolicy} />);

    const policyTrigger = screen.getByTestId("policy-selector-trigger");
    await user.click(policyTrigger);

    expect(screen.getByText("Adding directly to your personal shelf")).toBeInTheDocument();
    expect(screen.getByTestId("policy-option-wishlist")).toBeInTheDocument();
    expect(screen.getByTestId("policy-option-catalog")).toBeInTheDocument();

    await user.click(screen.getByTestId("policy-option-wishlist"));
    expect(setPolicy).toHaveBeenCalledWith("wishlist");
  });

  it("flash toggle button renders when hasFlash is true and hides when false", () => {
    const { rerender } = render(
      <TopBar
        currentFormat="book"
        setFormat={setFormat}
        hasFlash={true}
        isFlashOn={false}
        onToggleFlash={onToggleFlash}
      />
    );

    const flashBtn = screen.getByLabelText("Toggle flash");
    fireEvent.click(flashBtn);
    expect(onToggleFlash).toHaveBeenCalled();

    rerender(<TopBar currentFormat="book" setFormat={setFormat} hasFlash={false} />);
    expect(screen.queryByLabelText("Toggle flash")).not.toBeInTheDocument();
  });

  it("back-link invokes cancel callback", () => {
    render(<TopBar currentFormat="book" setFormat={setFormat} onCancel={onCancel} />);

    const backLink = screen.getByLabelText("Go back to library");
    fireEvent.click(backLink);
    expect(onCancel).toHaveBeenCalled();
  });
});
