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
import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ManifestationPage from "@/app/manifestation/[id]/page";
import ItemPage from "@/app/item/[id]/page";
import SharedCollectionPage from "@/app/share/[token]/page";
import PublicProfilePage from "@/app/u/[username]/page";
import CollectionLayout from "@/app/collection/layout";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
  }),
  useParams: () => ({ id: "100" }),
  useSearchParams: () => new URLSearchParams(),
  notFound: vi.fn(),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
  Navbar: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/navbar", () => ({
  Navbar: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
  default: (props: React.ComponentProps<"img">) => <img {...props} />,
}));

vi.mock("next-intl/server", () => ({
  getTranslations: async () => (key: string) => key,
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

const createTestQueryClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderWithClient = (component: React.ReactElement) => {
  const client = createTestQueryClient();
  return render(<QueryClientProvider client={client}>{component}</QueryClientProvider>);
};

describe("External AI Agent Semantic Discoverability across Public SSR Pages", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("manifestation page delivers Schema.org JSON-LD directly in SSR stream for crawlers like Gemini", async () => {
    const mockManifestation = {
      id: 2053,
      title: "The Singles 1992 - 2003",
      authors: ["No Doubt"],
      content_type: "music",
      format: "cd",
      work_id: 1993,
      meta: {
        Publisher: "Interscope Records",
        Year: "2003",
        language: "en",
      },
    };

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockManifestation }),
    } as unknown as Response);

    // Simulate Server Component execution on HTTP GET
    const pageJsx = await ManifestationPage({ params: Promise.resolve({ id: "2053" }) });
    const { container } = renderWithClient(pageJsx);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();
    const parsed = JSON.parse(scriptTag!.textContent || "{}");

    expect(parsed["@context"]).toBe("https://schema.org");
    expect(parsed["@type"]).toBe("MusicAlbum");
    expect(parsed["name"]).toBe("The Singles 1992 - 2003");
    expect(parsed["author"]["name"]).toBe("No Doubt");
    expect(parsed["inLanguage"]).toBe("en");
  });

  it("shared collection page delivers CollectionPage Schema.org JSON-LD in SSR stream", async () => {
    const mockSharedCollection = {
      author: "Sebastian Kruk",
      collection_name: "My wish list Items",
      collection_description: "Curated wishlist items for testing",
      items: [
        { id: 101, manifestation_id: 1996, title: "Odyseja", authors: ["Stephen Fry"] },
        { id: 102, manifestation_id: 2010, title: "Physics of the Future", authors: ["Michio Kaku"] },
      ],
    };

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockSharedCollection }),
    } as unknown as Response);

    const pageJsx = await SharedCollectionPage({ params: Promise.resolve({ token: "test-token-123" }) });
    const { container } = renderWithClient(pageJsx);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();
    const parsed = JSON.parse(scriptTag!.textContent || "{}");

    expect(parsed["@context"]).toBe("https://schema.org");
    expect(parsed["@type"]).toBe("CollectionPage");
    expect(parsed["name"]).toBe("My wish list Items");
    expect(parsed["author"]["name"]).toBe("Sebastian Kruk");
    expect(parsed["numberOfItems"]).toBe(2);
    expect(parsed["mainEntity"]["itemListElement"]).toHaveLength(2);
  });

  it("public user profile page delivers ProfilePage Schema.org JSON-LD in SSR stream", async () => {
    const mockProfile = {
      username: "sebastian",
      display_name: "Sebastian Kruk",
      bio: "Collector and architect",
      avatar_url: "https://example.com/avatar.jpg",
    };

    vi.spyOn(global, "fetch").mockImplementation(async (url: any) => {
      const urlStr = String(url);
      if (urlStr.includes("/items")) {
        return {
          ok: true,
          json: async () => ({ success: true, data: { items: [{ id: 1, title: "Book 1" }] } }),
        } as unknown as Response;
      }
      return {
        ok: true,
        json: async () => ({ success: true, data: mockProfile }),
      } as unknown as Response;
    });

    const pageJsx = await PublicProfilePage({ params: Promise.resolve({ username: "sebastian" }) });
    const { container } = renderWithClient(pageJsx);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();
    const parsed = JSON.parse(scriptTag!.textContent || "{}");

    expect(parsed["@context"]).toBe("https://schema.org");
    expect(parsed["@type"]).toBe("ProfilePage");
    expect(parsed["name"]).toBe("Sebastian Kruk's Library");
    expect(parsed["mainEntity"]["name"]).toBe("Sebastian Kruk");
    expect(parsed["mainEntity"]["alternateName"]).toBe("sebastian");
    expect(parsed["hasPart"]["numberOfItems"]).toBe(1);
  });

  it("item page delivers CreativeWork FRBR hierarchy JSON-LD in SSR stream", async () => {
    const mockItem = {
      id: 55,
      title: "Dune",
      authors: ["Frank Herbert"],
      manifestation_id: 12,
      work: {
        id: 7,
        title: "Dune",
        authors: ["Frank Herbert"],
      },
      expression: {
        id: 9,
        language: "en",
        content_type: "text",
      },
    };

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockItem }),
    } as unknown as Response);

    const pageJsx = await ItemPage({ params: Promise.resolve({ id: "55" }) });
    const { container } = renderWithClient(pageJsx);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();
    const parsed = JSON.parse(scriptTag!.textContent || "{}");

    expect(parsed["@context"]).toBe("https://schema.org");
    expect(parsed["@type"]).toBe("CreativeWork");
    expect(parsed["name"]).toBe("Dune");
    expect(parsed["author"]["name"]).toBe("Frank Herbert");
    expect(Array.isArray(parsed["workExample"])).toBe(true);
  });

  it("collection layout injects baseline CollectionPage JSON-LD on catalog routes", () => {
    const { container } = render(
      <CollectionLayout>
        <div data-testid="child-content">Catalog</div>
      </CollectionLayout>
    );

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();
    const parsed = JSON.parse(scriptTag!.textContent || "{}");

    expect(parsed["@context"]).toBe("https://schema.org");
    expect(parsed["@type"]).toBe("CollectionPage");
    expect(parsed["name"]).toBe("iqoqo Library Collection");
  });
});
