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
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SidebarFilters } from "@/components/collection/sidebar-filters";
import type { ActiveFilter } from "@/components/collection/filter-bar";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: () => ({ data: { id: "user-1", email: "user@test.local" }, isLoading: false }),
  useTaxonomies: () => ({ data: { text: { genres: [], formats: [] } }, isLoading: false }),
}));

/**
 * Helper to render components wrapped in a QueryClientProvider for tests.
 *
 * @param {React.ReactElement} ui - The component to render.
 * @returns {ReturnType<typeof render>} Render result.
 */
function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("SidebarFilters - Ownership Facet", () => {
  const defaultProps = {
    selectedCategory: "text",
    onSelectCategory: vi.fn(),
    activeFilters: [] as ActiveFilter[],
    onToggleFilter: vi.fn(),
    onClearFilters: vi.fn(),
    isLoggedIn: true,
  };

  it("renders the Ownership facet with Owned and Not Owned options", () => {
    renderWithClient(<SidebarFilters {...defaultProps} />);

    expect(screen.getByText("Ownership")).toBeInTheDocument();
    expect(screen.getByText("Owned")).toBeInTheDocument();
    expect(screen.getByText("Not Owned")).toBeInTheDocument();
  });

  it("triggers onToggleFilter with ownership when Owned checkbox is clicked", () => {
    const onToggleFilter = vi.fn();
    renderWithClient(<SidebarFilters {...defaultProps} onToggleFilter={onToggleFilter} />);

    const ownedLabel = screen.getByText("Owned");
    fireEvent.click(ownedLabel);

    expect(onToggleFilter).toHaveBeenCalledWith({ type: "ownership", value: "owned" });
  });

  it("triggers onToggleFilter with ownership when Not Owned checkbox is clicked", () => {
    const onToggleFilter = vi.fn();
    renderWithClient(<SidebarFilters {...defaultProps} onToggleFilter={onToggleFilter} />);

    const notOwnedLabel = screen.getByText("Not Owned");
    fireEvent.click(notOwnedLabel);

    expect(onToggleFilter).toHaveBeenCalledWith({ type: "ownership", value: "not_owned" });
  });

  it("shows active state when ownership filter is active", () => {
    const activeFilters: ActiveFilter[] = [{ type: "ownership", value: "owned" }];
    renderWithClient(<SidebarFilters {...defaultProps} activeFilters={activeFilters} />);

    const ownedCheckbox = screen.getByRole("checkbox", { name: "Owned" });
    expect(ownedCheckbox).toBeChecked();

    const notOwnedCheckbox = screen.getByRole("checkbox", { name: "Not Owned" });
    expect(notOwnedCheckbox).not.toBeChecked();
  });

  it("shows all items when no ownership facet is selected (no empty state)", () => {
    const activeFilters: ActiveFilter[] = [];
    renderWithClient(<SidebarFilters {...defaultProps} activeFilters={activeFilters} />);

    const ownedCheckbox = screen.getByRole("checkbox", { name: "Owned" });
    expect(ownedCheckbox).not.toBeChecked();

    const notOwnedCheckbox = screen.getByRole("checkbox", { name: "Not Owned" });
    expect(notOwnedCheckbox).not.toBeChecked();

    expect(screen.queryByText(/no items found/i)).not.toBeInTheDocument();
  });
});
