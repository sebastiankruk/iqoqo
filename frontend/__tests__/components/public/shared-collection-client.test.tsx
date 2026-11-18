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
import { buildPaginationWindow } from "@/lib/pagination";
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

  it("renders subtle RDF icon button linking to query-free /jsonld/1 and sr-only windowed AI page links", () => {
    const { container } = render(
      <SharedCollectionClient
        initialToken="tok-123"
        publicBaseUrl="https://preview.iqoqo.cc"
        initialData={{
          author: "audiophile",
          collection_name: "Jazz Vinyl",
          total: 365,
          page: 1,
          per_page: 48,
          pages: 8,
          items: [
            {
              id: 1,
              manifestation_id: 10,
              title: "Kind of Blue",
              authors: ["Miles Davis"],
              content_type: "music",
              format: "vinyl",
            },
          ],
        }}
      />
    );

    expect(container.querySelector('[data-testid="shared-catalog-index"]')).toBeNull();
    expect(screen.getByText("365 Items")).toBeInTheDocument();

    const jsonLdLink = screen.getByRole("link", { name: "jsonLdFeed" });
    expect(jsonLdLink).toHaveAttribute("href", "https://preview.iqoqo.cc/share/tok-123/jsonld/1");

    const aiNav = screen.getByRole("navigation", { name: "AI JSON-LD pages" });
    const aiLinks = Array.from(aiNav.querySelectorAll("a")).map(a => a.getAttribute("href"));
    expect(aiLinks).toEqual([
      "https://preview.iqoqo.cc/share/tok-123/jsonld/1",
      "https://preview.iqoqo.cc/share/tok-123/jsonld/2",
      "https://preview.iqoqo.cc/share/tok-123/jsonld/3",
      "https://preview.iqoqo.cc/share/tok-123/jsonld/4",
      "https://preview.iqoqo.cc/share/tok-123/jsonld/5",
      "https://preview.iqoqo.cc/share/tok-123/jsonld/6",
      "https://preview.iqoqo.cc/share/tok-123/jsonld/7",
    ]);

    const rssLink = screen.getByRole("link", { name: "RSS" });
    expect(rssLink).toHaveAttribute("href", "/share/tok-123/feed.xml");
  });

  it("caps pagination links to at most 10 pages (first, 8 around current, last)", () => {
    expect(buildPaginationWindow(1, 5)).toEqual([1, 2, 3, 4, 5]);
    expect(buildPaginationWindow(12, 25)).toEqual([1, 9, 10, 11, 12, 13, 14, 15, 16, 25]);
    expect(buildPaginationWindow(25, 25)).toEqual([1, 17, 18, 19, 20, 21, 22, 23, 24, 25]);

    render(
      <SharedCollectionClient
        initialToken="tok-25p"
        publicBaseUrl="https://preview.iqoqo.cc"
        initialData={{
          author: "collector",
          collection_name: "Huge Collection",
          total: 1200,
          page: 12,
          per_page: 48,
          pages: 25,
          items: [{ id: 1, manifestation_id: 10, title: "Album 1", authors: ["Artist"] }],
        }}
      />
    );

    const navs = screen.getAllByRole("navigation", { name: "Collection pagination" });
    const pageLinks = navs[0].querySelectorAll("a[href^='/share/tok-25p?page=']");
    // 10 numbered pages + Prev + Next = 12 links
    expect(pageLinks).toHaveLength(12);
    expect(navs[0].querySelector('a[aria-current="page"]')).toHaveTextContent("12");
  });

  it("updates displayed page immediately when initialData changes on client navigation", () => {
    const { rerender } = render(
      <SharedCollectionClient
        initialToken="tok-nav"
        publicBaseUrl="https://preview.iqoqo.cc"
        initialData={{
          author: "collector",
          collection_name: "Jazz",
          total: 96,
          page: 1,
          per_page: 48,
          pages: 2,
          items: [{ id: 1, manifestation_id: 10, title: "Page 1 Album", authors: ["Artist 1"] }],
        }}
      />
    );

    expect(
      screen.getAllByRole("navigation", { name: "Collection pagination" })[0].querySelector('a[aria-current="page"]')
    ).toHaveTextContent("1");

    rerender(
      <SharedCollectionClient
        initialToken="tok-nav"
        publicBaseUrl="https://preview.iqoqo.cc"
        initialData={{
          author: "collector",
          collection_name: "Jazz",
          total: 96,
          page: 2,
          per_page: 48,
          pages: 2,
          items: [{ id: 2, manifestation_id: 20, title: "Page 2 Album", authors: ["Artist 2"] }],
        }}
      />
    );

    expect(
      screen.getAllByRole("navigation", { name: "Collection pagination" })[0].querySelector('a[aria-current="page"]')
    ).toHaveTextContent("2");
  });
});
