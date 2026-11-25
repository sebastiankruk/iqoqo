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
import { ExpressionDetailClient } from "@/components/expression/expression-detail-client";
import type { ExpressionDetail } from "@/types/frbr";

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
    useExpression: (_id: number, initial?: ExpressionDetail | null) => ({ data: initial, isLoading: false }),
  };
});

const mockExpression: ExpressionDetail = {
  id: 2062,
  work_id: 1993,
  work_title: "The Singles 1992 - 2003",
  authors: ["No Doubt"],
  content_type: "music",
  language: "en",
  kind: null,
  is_live_performance: false,
  manifestations: [],
};

/** Render helper with a fresh QueryClient. */
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ExpressionDetailClient graph entry consistency (C149)", () => {
  beforeEach(() => {
    activeLocale = "en";
  });

  it("renders Explore Graph in the top utility bar in English", () => {
    renderWithQuery(<ExpressionDetailClient expressionId={2062} initialExpression={mockExpression} />);

    const link = screen.getByTestId("explore-graph-link");
    expect(link).toHaveAttribute("href", "/graph?type=expression&id=2062");
    expect(link).toHaveTextContent("Explore Graph");
  });

  it("renders localized Polish graph.exploreGraph label with no hardcoded English fallback", () => {
    activeLocale = "pl";
    renderWithQuery(<ExpressionDetailClient expressionId={2062} initialExpression={mockExpression} />);

    const link = screen.getByTestId("explore-graph-link");
    expect(link).toHaveTextContent("Eksploruj graf");
    expect(link).not.toHaveTextContent("Explore Graph");
  });
});
