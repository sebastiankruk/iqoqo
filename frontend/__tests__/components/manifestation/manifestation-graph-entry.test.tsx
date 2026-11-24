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
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import enMessages from "@/messages/en.json";
import plMessages from "@/messages/pl.json";
import { ManifestationDetailClient } from "@/components/manifestation/manifestation-detail-client";
import type { CatalogEntry } from "@/types/frbr";

let activeLocale: "en" | "pl" = "en";

vi.mock("next-intl", () => ({
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
  useLocale: () => activeLocale,
  useTranslations: (namespace?: string) => {
    const messages = activeLocale === "pl" ? plMessages : enMessages;
    let dictionary: unknown = messages;
    if (namespace) {
      for (const segment of namespace.split(".")) {
        dictionary =
          dictionary && typeof dictionary === "object" ? (dictionary as Record<string, unknown>)[segment] : undefined;
      }
    }
    return (key: string) => {
      let translation: unknown = dictionary;
      for (const segment of key.split(".")) {
        translation =
          translation && typeof translation === "object"
            ? (translation as Record<string, unknown>)[segment]
            : undefined;
      }
      return typeof translation === "string" ? translation : key;
    };
  },
}));

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
    useManifestation: (_id: number, initial?: CatalogEntry | null) => ({
      data: initial,
      isLoading: false,
      isError: false,
    }),
    useProfile: () => ({ data: { id: "user-1", email: "reader@iqoqo.local", permissions: [] } }),
    useWorkParts: () => ({ data: { data: [] } }),
    useUserCollections: () => ({ data: [], isLoading: false }),
  };
});

vi.mock("@/lib/api/wishlist", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/wishlist")>();
  return {
    ...actual,
    useDeleteWishlistItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

const mockManifestation: CatalogEntry = {
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

/** Render helper with a fresh QueryClient. */
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ManifestationDetailClient graph entry consistency (C149)", () => {
  beforeEach(() => {
    activeLocale = "en";
  });

  it("renders Explore Graph inside the top utility bar in English", () => {
    renderWithQuery(<ManifestationDetailClient manifestationId={123} initialManifestation={mockManifestation} />);

    const topBar = screen.getByTestId("manifestation-top-bar");
    const link = screen.getByTestId("explore-graph-link");
    expect(topBar).toContainElement(link);
    expect(link).toHaveAttribute("href", "/graph?type=manifestation&id=123");
    expect(link).toHaveTextContent("Explore Graph");
  });

  it("renders localized Polish graph.exploreGraph label with no hardcoded English fallback", () => {
    activeLocale = "pl";
    renderWithQuery(<ManifestationDetailClient manifestationId={123} initialManifestation={mockManifestation} />);

    const link = screen.getByTestId("explore-graph-link");
    expect(link).toHaveTextContent("Eksploruj graf");
    expect(link).not.toHaveTextContent("Explore Graph");
  });
});
