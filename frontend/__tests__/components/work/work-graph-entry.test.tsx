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
import { WorkDetailClient } from "@/components/work/work-detail-client";
import type { WorkDetail } from "@/types/frbr";

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

vi.mock("@/lib/api/hooks", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks")>();
  return {
    ...actual,
    useWork: (_id: number, initial?: WorkDetail | null) => ({ data: initial, isLoading: false }),
    useProfile: () => ({ data: { id: "user-1", email: "reader@iqoqo.local", permissions: [] } }),
  };
});

vi.mock("@/lib/api/wishlist", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/wishlist")>();
  return {
    ...actual,
    useWishlist: () => ({ data: { data: [] } }),
    useCreateWishlistItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useDeleteWishlistItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

const mockWork: WorkDetail = {
  id: 1993,
  title: "The Singles 1992 - 2003",
  work_kind: "serial",
  issn: "1507-5966",
  authors: ["No Doubt"],
  meta: {},
  expressions: [],
};

/** Render helper with a fresh QueryClient. */
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("WorkDetailClient graph entry consistency (C149)", () => {
  beforeEach(() => {
    activeLocale = "en";
  });

  it("renders Explore Graph in the top utility bar outside the hero CTA cluster in English", () => {
    renderWithQuery(<WorkDetailClient workId={1993} initialWork={mockWork} />);

    const link = screen.getByTestId("explore-graph-link");
    expect(link).toHaveAttribute("href", "/graph?type=work&id=1993");
    expect(link).toHaveTextContent("Explore Graph");

    // Must be in the top utility bar alongside Back, not inside the hero Add Issue CTA row
    const addIssueCta = screen.getByTestId("work-add-issue-cta");
    expect(addIssueCta.parentElement).not.toContainElement(link);
    expect(screen.getByRole("button", { name: /back/i }).parentElement).toContainElement(link);
  });

  it("renders localized Polish graph.exploreGraph label with no hardcoded English fallback", () => {
    activeLocale = "pl";
    renderWithQuery(<WorkDetailClient workId={1993} initialWork={mockWork} />);

    const link = screen.getByTestId("explore-graph-link");
    expect(link).toHaveTextContent("Eksploruj graf");
    expect(link).not.toHaveTextContent("Explore Graph");
  });
});
