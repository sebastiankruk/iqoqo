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

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ManifestationDetailClient } from "@/components/manifestation/manifestation-detail-client";
import type { CatalogEntry } from "@/types/frbr";
import { toast } from "sonner";

const mockDeleteMutateAsync = vi.fn();
const mockUseManifestation = vi.fn();
const mockUseProfile = vi.fn();
const mockUseWorkParts = vi.fn();
const mockUseUserCollections = vi.fn();

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

vi.mock("@/components/manifestation/manifestation-actions", () => ({
  ManifestationActions: () => null,
}));

vi.mock("@/components/manifestation/semantic-links", () => ({
  SemanticLinks: () => null,
}));

vi.mock("@/components/social/frbr-feedback", () => ({
  FRBRFeedback: () => null,
}));

vi.mock("@/components/item/extended-metadata", () => ({
  ExtendedMetadata: () => null,
}));

vi.mock("@/components/cover/cover-provenance", () => ({
  CoverProvenance: () => null,
}));

vi.mock("@/lib/api/hooks", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks")>();
  return {
    ...actual,
    useManifestation: (id: number, initial?: CatalogEntry | null) => mockUseManifestation(id, initial),
    useProfile: () => mockUseProfile(),
    useWorkParts: () => mockUseWorkParts(),
    useUserCollections: () => mockUseUserCollections(),
  };
});

vi.mock("@/lib/api/wishlist", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/wishlist")>();
  return {
    ...actual,
    useDeleteWishlistItem: () => ({ mutateAsync: mockDeleteMutateAsync, isPending: false }),
  };
});

/** Render component wrapped in QueryClientProvider. */
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const baseManifestation: CatalogEntry = {
  id: 123,
  expression_id: 45,
  work_id: 67,
  title: "The Left Hand of Darkness",
  authors: ["Ursula K. Le Guin"],
  isbn13: "9780441478125",
  user_owns: false,
  item_id: null,
  wishlist_item_id: null,
  content_type: "text",
  meta: {},
};

describe("ManifestationDetailClient wishlist awareness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: { id: "user-1", email: "reader@iqoqo.local", permissions: [] } });
    mockUseWorkParts.mockReturnValue({ data: { data: [] } });
    mockUseUserCollections.mockReturnValue({ data: [], isLoading: false });
  });

  it("shows On Wishlist badge, Move to Collection CTA, and direct Remove from wishlist button when wishlisted", async () => {
    mockUseManifestation.mockReturnValue({
      data: { ...baseManifestation, wishlist_item_id: 789 },
      isLoading: false,
      isError: false,
    });
    mockDeleteMutateAsync.mockResolvedValueOnce(undefined);

    renderWithQuery(<ManifestationDetailClient manifestationId={123} initialManifestation={baseManifestation} />);

    expect(screen.getByTestId("on-wishlist-badge")).toHaveTextContent("On Wishlist");
    expect(screen.getByRole("button", { name: /move to collection/i })).toBeInTheDocument();

    const removeBtn = screen.getByRole("button", { name: /remove from wishlist/i });
    expect(removeBtn).toBeInTheDocument();
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith(789);
      expect(toast.success).toHaveBeenCalledWith("Removed from wishlist");
    });
  });

  it("hides On Wishlist badge and direct removal button when not on wishlist", () => {
    mockUseManifestation.mockReturnValue({
      data: baseManifestation,
      isLoading: false,
      isError: false,
    });

    renderWithQuery(<ManifestationDetailClient manifestationId={123} initialManifestation={baseManifestation} />);

    expect(screen.queryByTestId("on-wishlist-badge")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add to collection/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /remove from wishlist/i })).not.toBeInTheDocument();
  });

  it("hides wishlist badge and shows owned actions when user owns the item", () => {
    mockUseManifestation.mockReturnValue({
      data: { ...baseManifestation, user_owns: true, item_id: 55, wishlist_item_id: null },
      isLoading: false,
      isError: false,
    });

    renderWithQuery(<ManifestationDetailClient manifestationId={123} initialManifestation={baseManifestation} />);

    expect(screen.queryByTestId("on-wishlist-badge")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /view my item/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /remove from wishlist/i })).not.toBeInTheDocument();
  });
});
