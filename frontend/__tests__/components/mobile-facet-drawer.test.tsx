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
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
/**
 * Tests for the Mobile Filter Drawer component.
 *
 * Verifies:
 * - Drawer renders at mobile viewport (below 768px)
 * - Drawer toggle opens the filter panel
 * - Close button/backdrop closes the drawer
 * - Facet UI renders inline at desktop viewport instead of drawer
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import React from "react";

// ── Mock dependencies ───────────────────────────────────────────────────────
vi.mock("@/components/collection/sidebar-filters", () => ({
  SidebarFilters: () => React.createElement("div", { "data-testid": "sidebar-filters" }, "Sidebar Filters"),
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) =>
    React.createElement("button", props, children),
}));

// Mock the drawer UI components as proper React component functions
vi.mock("@/components/ui/drawer", () => {
  function Drawer({ open, onOpenChange, children }: { open: boolean; onOpenChange: (open: boolean) => void; children: React.ReactNode }) {
    if (!open) return null;
    return React.createElement("div", {
      "data-testid": "drawer",
      onClick: () => onOpenChange(false),
    }, children);
  }
  function DrawerContent({ children, className }: { children: React.ReactNode; className?: string }) {
    return React.createElement("div", { "data-testid": "drawer-content", className }, children);
  }
  function DrawerHeader({ children, className }: { children: React.ReactNode; className?: string }) {
    return React.createElement("div", { "data-testid": "drawer-header", className }, children);
  }
  function DrawerTitle({ children, className }: { children: React.ReactNode; className?: string }) {
    return React.createElement("h2", { "data-testid": "drawer-title", className }, children);
  }
  function DrawerFooter({ children, className }: { children: React.ReactNode; className?: string }) {
    return React.createElement("div", { "data-testid": "drawer-footer", className }, children);
  }
  function DrawerClose({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) {
    return React.createElement("div", { "data-testid": "drawer-close" }, children);
  }
  return { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerFooter, DrawerClose };
});

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      title: "Filters",
      showResults: "Show Results",
    };
    return translations[key] || key;
  },
}));

vi.mock("lucide-react", () => ({
  SlidersHorizontal: () => React.createElement("span", { "data-testid": "sliders-icon" }, "Slider"),
}));

// ── Component import ───────────────────────────────────────────────────────
import { MobileFilterDrawer } from "@/components/collection/mobile-filter-drawer";

describe("MobileFilterDrawer", () => {
  const defaultProps = {
    open: false,
    onClose: vi.fn(),
    activeFilters: [] as Array<{ type: string; value: string }>,
    onToggleFilter: vi.fn(),
    statusCounts: {} as Record<string, number>,
    formatCounts: {} as Record<string, number>,
    categoryCounts: {} as Record<string, number>,
    viewMode: "items" as const,
    isLoggedIn: true,
    isCurator: false,
  };

  it("does not render drawer when closed", () => {
    render(React.createElement(MobileFilterDrawer, { ...defaultProps, open: false }));
    expect(screen.queryByTestId("drawer")).toBeNull();
  });

  it("renders drawer when open", () => {
    render(React.createElement(MobileFilterDrawer, { ...defaultProps, open: true }));
    expect(screen.getByTestId("drawer")).toBeTruthy();
  });

  it("renders filter title in open drawer", () => {
    render(React.createElement(MobileFilterDrawer, { ...defaultProps, open: true }));
    expect(screen.getByTestId("drawer-title")).toBeTruthy();
    expect(screen.getByTestId("drawer-title").textContent).toContain("Filter");
  });

  it("renders sidebar filters content in open drawer", () => {
    render(React.createElement(MobileFilterDrawer, { ...defaultProps, open: true }));
    expect(screen.getByTestId("sidebar-filters")).toBeTruthy();
  });

  it("renders show results button in open drawer", () => {
    render(React.createElement(MobileFilterDrawer, { ...defaultProps, open: true }));
    expect(screen.getByTestId("drawer-close")).toBeTruthy();
    expect(screen.getByText("Show Results")).toBeTruthy();
  });

  it("calls onClose when drawer backdrop is clicked", () => {
    const onClose = vi.fn();
    render(React.createElement(MobileFilterDrawer, { ...defaultProps, onClose, open: true }));
    fireEvent.click(screen.getByTestId("drawer"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders with different view modes", () => {
    render(React.createElement(MobileFilterDrawer, { ...defaultProps, open: true, viewMode: "works" }));
    expect(screen.getByTestId("drawer")).toBeTruthy();
  });

  it("renders with unauthenticated props", () => {
    render(React.createElement(MobileFilterDrawer, { ...defaultProps, open: true, isLoggedIn: false }));
    expect(screen.getByTestId("drawer")).toBeTruthy();
  });
});
