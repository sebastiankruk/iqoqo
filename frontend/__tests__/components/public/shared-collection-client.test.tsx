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

import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SharedCollectionClient } from "@/components/public/shared-collection-client";
import * as routeParams from "@/lib/capacitor/route-params";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar">Navbar</nav>,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer">Footer</footer>,
}));

vi.mock("@/components/ui/share-button", () => ({
  ShareButton: () => <button>Share</button>,
}));

vi.mock("@/components/ui/public-feed-button", () => ({
  PublicFeedButton: ({ feedPath, label }: { feedPath: string; label?: string }) => (
    <a href={feedPath}>{label || "RSS"}</a>
  ),
}));

vi.mock("@/components/collection/collection-grid", () => ({
  CollectionGrid: ({ items }: { items: unknown[] }) => (
    <div data-testid="collection-grid">Items count: {items.length}</div>
  ),
}));

describe("SharedCollectionClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders initial SSR data directly without fetching", () => {
    const mockData = {
      author: "alice",
      collection_name: "Favorite Sci-Fi",
      collection_description: "Great books",
      items: [
        {
          id: 1,
          manifestation_id: 101,
          title: "Dune",
          authors: ["Frank Herbert"],
        },
      ],
    };

    render(<SharedCollectionClient initialData={mockData} initialToken="token-123" />);

    expect(screen.getByText("Favorite Sci-Fi")).toBeInTheDocument();
    expect(screen.getByText("@alice")).toBeInTheDocument();
    expect(screen.getByText("Great books")).toBeInTheDocument();
    expect(screen.getByTestId("collection-grid")).toHaveTextContent("Items count: 1");
  });

  it("client-hydrates and fetches collection when resolved via useResolvedRouteParam", async () => {
    vi.spyOn(routeParams, "useResolvedRouteParam").mockReturnValue("native-token-abc");

    const mockResponse = {
      success: true,
      data: {
        author: "bob",
        collection_name: "Mobile Collection",
        collection_description: "Loaded on Android/iOS",
        items: [
          { id: 2, manifestation_id: 202, title: "Neuromancer", authors: ["William Gibson"] },
          { id: 3, manifestation_id: 203, title: "Snow Crash", authors: ["Neal Stephenson"] },
        ],
      },
    };

    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => mockResponse,
    } as Response);

    render(<SharedCollectionClient initialData={null} initialToken="_placeholder" />);

    await waitFor(() => {
      expect(screen.getByText("Mobile Collection")).toBeInTheDocument();
    });

    expect(screen.getByText("@bob")).toBeInTheDocument();
    expect(screen.getByTestId("collection-grid")).toHaveTextContent("Items count: 2");
    expect(fetchSpy).toHaveBeenCalled();
  });

  it("displays not found state when API returns 404", async () => {
    vi.spyOn(routeParams, "useResolvedRouteParam").mockReturnValue("expired-token");

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
    } as Response);

    render(<SharedCollectionClient initialData={null} initialToken="_placeholder" />);

    await waitFor(() => {
      expect(screen.getByText("Collection Not Found")).toBeInTheDocument();
    });
  });

  it("renders non-API JSON-LD / AI Feed and RSS links for shared collections", () => {
    render(
      <SharedCollectionClient
        initialToken="tok-123"
        initialData={{
          author: "audiophile",
          collection_name: "Jazz Vinyl",
          items: [
            {
              id: 1,
              manifestation_id: 10,
              title: "Kind of Blue",
              authors: ["Miles Davis"],
              content_type: "music",
              format: "vinyl",
              publisher: "Columbia",
              catalog_number: "CL 1355",
              publication_year: 1959,
              ean: "886973355220",
            },
          ],
        }}
      />
    );

    const jsonLdLink = screen.getByRole("link", { name: "jsonLdFeed" });
    expect(jsonLdLink).toHaveAttribute("href", "/share/tok-123/catalog.jsonld");

    const rssLink = screen.getByRole("link", { name: "RSS" });
    expect(rssLink).toHaveAttribute("href", "/share/tok-123/feed.xml");
  });

  it("renders compact SSR catalog index with all 400 items before the collection grid", () => {
    const items = Array.from({ length: 400 }, (_, i) => ({
      id: i + 1,
      manifestation_id: 1000 + i,
      title: `Album ${i + 1}`,
      authors: [`Artist ${i + 1}`],
      content_type: "music",
      format: i % 2 === 0 ? "vinyl" : "cd",
      publisher: "Blue Note",
      catalog_number: `BN-${i + 1}`,
      publication_year: 1965,
    }));

    const { container } = render(
      <SharedCollectionClient
        initialToken="tok-400"
        initialData={{
          author: "collector",
          collection_name: "Large Jazz Catalog",
          items,
        }}
      />
    );

    const indexEl = screen.getByTestId("shared-catalog-index");
    expect(indexEl).toHaveAttribute("open");
    const listItems = indexEl.querySelectorAll("li");
    expect(listItems).toHaveLength(400);
    expect(listItems[0].textContent).toContain("Album 1 — Artist 1 [vinyl · Blue Note · BN-1 · 1965]");
    expect(listItems[399].textContent).toContain("Album 400 — Artist 400 [cd · Blue Note · BN-400 · 1965]");

    const gridEl = screen.getByTestId("collection-grid");
    const html = container.innerHTML;
    expect(html.indexOf("shared-catalog-index")).toBeLessThan(html.indexOf("collection-grid"));
    expect(gridEl).toHaveTextContent("Items count: 400");
  });
});
