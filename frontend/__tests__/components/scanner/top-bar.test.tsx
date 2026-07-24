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

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TopBar } from "@/components/scanner/top-bar";

// Mock next/link to just render children
vi.mock("next/link", () => ({
  default: ({ children, ...props }: { children: React.ReactNode; href: string; [key: string]: unknown }) => (
    <a {...props}>{children}</a>
  ),
}));

// Mock next-intl
vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: () => (key: string) => key,
}));

describe("TopBar", () => {
  it("renders Scan New Item heading", () => {
    render(<TopBar />);
    expect(screen.getByText("Scan New Item")).toBeTruthy();
  });

  it("renders policy buttons when setPolicy is provided", () => {
    const setPolicy = vi.fn();
    render(<TopBar setPolicy={setPolicy} />);
    expect(screen.getByText("Inventory")).toBeTruthy();
    expect(screen.getByText("Wishlist")).toBeTruthy();
    expect(screen.getByText("Catalog")).toBeTruthy();
  });

  it("calls onCancel when back link is clicked", () => {
    const onCancel = vi.fn();
    render(<TopBar onCancel={onCancel} />);
    fireEvent.click(screen.getByLabelText("Go back to library"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("renders flash toggle button when hasFlash is true", () => {
    render(<TopBar hasFlash={true} isFlashOn={false} />);
    expect(screen.getByLabelText("Toggle flash")).toBeTruthy();
  });

  it("calls onToggleFlash when flash button is clicked", () => {
    const onToggleFlash = vi.fn();
    render(<TopBar hasFlash={true} isFlashOn={false} onToggleFlash={onToggleFlash} />);
    fireEvent.click(screen.getByLabelText("Toggle flash"));
    expect(onToggleFlash).toHaveBeenCalledOnce();
  });

  it("does not render flash button when hasFlash is falsy", () => {
    render(<TopBar />);
    expect(screen.queryByLabelText("Toggle flash")).toBeNull();
  });

  it("renders format buttons when setFormat is provided", () => {
    const setFormat = vi.fn();
    render(<TopBar currentFormat="book" setFormat={setFormat} />);
    // Format buttons are rendered as <button> elements; just verify they exist
    const buttons = screen.getAllByRole("button");
    // Back button + format buttons (at least 2 for book and another format)
    expect(buttons.length).toBeGreaterThan(2);
  });
});
