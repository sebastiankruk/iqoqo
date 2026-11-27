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
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HelpHubPage from "@/app/help/page";
import { HELP_ARTICLES } from "@/lib/help-articles";
import { containsHtmlTags } from "@/components/ui/rich-text";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  useLocale: () => "en",
}));

vi.mock("@/components/dashboard/navbar", () => ({
  Navbar: () => <nav data-testid="navbar">Navbar</nav>,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer">Footer</footer>,
}));

describe("HelpHubPage", () => {
  it("renders help articles and categories", () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <HelpHubPage />
      </QueryClientProvider>
    );

    expect(screen.getByTestId("navbar")).toBeInTheDocument();
    expect(screen.getByTestId("footer")).toBeInTheDocument();
    expect(screen.getByText("Beyond the Bookshelf: How iqoqo Organizes Your World")).toBeInTheDocument();
    expect(screen.getByText("From Camera to Catalog: Scanning, Manual Entry & Curatorial Help")).toBeInTheDocument();
    expect(screen.getByText("The iqoqo Federation: Connected Libraries, Sovereign Data")).toBeInTheDocument();
    expect(screen.getByText("Privacy, Sharing & Social Interactions: The Hidden Gems")).toBeInTheDocument();
    expect(screen.getByText("The Curator's Handbook: Mastering Complex FRBR Cases")).toBeInTheDocument();
  });

  it("matches v1.1.0 features in both English and Polish article content and search", () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <HelpHubPage />
      </QueryClientProvider>
    );

    const searchInput = screen.getByPlaceholderText("searchPlaceholder");
    fireEvent.change(searchInput, { target: { value: "Friend Bonus" } });
    expect(screen.getByText("Privacy, Sharing & Social Interactions: The Hidden Gems")).toBeInTheDocument();
    expect(screen.queryByText("The iqoqo Federation: Connected Libraries, Sovereign Data")).not.toBeInTheDocument();

    const bySlug = Object.fromEntries(HELP_ARTICLES.map(article => [article.slug, article]));
    expect(bySlug["frbr-hierarchy"].content.en).toContain("F18_Serial_Work");
    expect(bySlug["frbr-hierarchy"].content.pl).toContain("F18_Serial_Work");
    expect(bySlug["frbr-hierarchy"].content.en).toContain("Visual Relation Graph");
    expect(bySlug["frbr-hierarchy"].content.pl).toContain("Graf Relacji FRBR");
    expect(bySlug["camera-to-catalog"].content.en).toContain("SerialDisambiguationModal");
    expect(bySlug["camera-to-catalog"].content.pl).toContain("GS1 `977`");
    expect(bySlug["privacy-sharing-social"].content.en).toContain("Bulk Visibility Toolbar");
    expect(bySlug["privacy-sharing-social"].content.pl).toContain("Bonus dla Znajomych");
    expect(bySlug["federation-architecture"].content.en).toContain("Valkey 8");
    expect(bySlug["federation-architecture"].content.pl).toContain("Valkey 8");
    expect(bySlug["curators-handbook"].content.en).toContain("/api/catalog/graph");
    expect(bySlug["curators-handbook"].content.pl).toContain("/api/catalog/graph");

    // Ensure markdown guide content never triggers HTML-mode fallback in RichText
    for (const article of HELP_ARTICLES) {
      expect(containsHtmlTags(article.content.en)).toBe(false);
      expect(containsHtmlTags(article.content.pl)).toBe(false);
    }
  });
});
