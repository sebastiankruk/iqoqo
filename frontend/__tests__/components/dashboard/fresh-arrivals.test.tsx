// frontend/__tests__/components/dashboard/fresh-arrivals.test.tsx

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
 * Tests for the FreshArrivals component.
 */
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
 * Tests for the FreshArrivals component on the dashboard.
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FreshArrivals } from "@/components/dashboard/fresh-arrivals";
import { useRecentManifestations } from "@/lib/api/hooks";
import type { CatalogEntry } from "@/types/frbr";

// Mock the API hooks
vi.mock("@/lib/api/hooks", () => ({
  useRecentManifestations: vi.fn(),
}));

const mockUseRecentManifestations = vi.mocked(useRecentManifestations);

// Sample global catalog entries
const SAMPLE_MANIFESTATIONS: CatalogEntry[] = [
  {
    id: 1,
    expression_id: 1,
    title: "Dune",
    authors: ["Frank Herbert"],
    meta: {},
    cover_url: "/test-cover.jpg",
    user_owns: false,
  },
  {
    id: 2,
    expression_id: 2,
    title: "Recursion",
    authors: ["Blake Crouch"],
    meta: {},
    user_owns: false,
  },
];

describe("FreshArrivals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default to an empty, loaded state
    mockUseRecentManifestations.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useRecentManifestations>);
  });

  it("renders the section heading", () => {
    render(<FreshArrivals />);
    expect(screen.getByRole("heading", { name: "Fresh Arrivals" })).toBeInTheDocument();
  });

  it("renders a 'View global library' link pointing to /collection?viewMode=manifestations", () => {
    render(<FreshArrivals />);
    const link = screen.getByRole("link", { name: /view global library/i });
    expect(link).toHaveAttribute("href", "/collection?view=manifestations");
  });

  it("does not show item titles while loading", () => {
    mockUseRecentManifestations.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useRecentManifestations>);

    render(<FreshArrivals />);
    expect(screen.queryByText("Dune")).not.toBeInTheDocument();
  });

  it("shows item titles when data is loaded", () => {
    mockUseRecentManifestations.mockReturnValue({
      data: SAMPLE_MANIFESTATIONS,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useRecentManifestations>);

    render(<FreshArrivals />);
    expect(screen.getByText("Dune")).toBeInTheDocument();
    expect(screen.getByText("Recursion")).toBeInTheDocument();
  });

  it("renders the book cover when cover_url is provided", () => {
    mockUseRecentManifestations.mockReturnValue({
      data: SAMPLE_MANIFESTATIONS,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useRecentManifestations>);

    render(<FreshArrivals />);
    const img = screen.getByAltText("Cover of Dune");
    expect(img).toBeInTheDocument();
  });

  it("shows an error message when the API fails", () => {
    mockUseRecentManifestations.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useRecentManifestations>);

    render(<FreshArrivals />);
    expect(screen.getByText(/api may be unavailable/i)).toBeInTheDocument();
  });

  it("renders item links pointing to the correct manifestation detail page", () => {
    mockUseRecentManifestations.mockReturnValue({
      data: SAMPLE_MANIFESTATIONS,
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useRecentManifestations>);

    render(<FreshArrivals />);

    // In React Testing Library with generic nested queries, checking closest link tag handles nested elements like spans
    const links = screen.getAllByRole("link", { name: /dune/i });
    expect(links[0].closest("a")).toHaveAttribute("href", "/manifestation/1");
  });

  it("is wrapped in a landmark section for accessibility", () => {
    render(<FreshArrivals />);
    expect(screen.getByRole("region", { name: /recently added items/i })).toBeInTheDocument();
  });
});
