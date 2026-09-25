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
 * SSR route tests verifying that JSON-LD payloads preserve original values
 * even when catalog and user-controlled inputs contain HTML-sensitive characters.
 */

import React from "react";
import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ManifestationPage from "@/app/manifestation/[id]/page";
import ItemPage from "@/app/item/[id]/page";
import SharedCollectionPage from "@/app/share/[token]/page";
import PublicProfilePage from "@/app/u/[username]/page";
import CollectionLayout from "@/app/collection/layout";
import { WorkStructuredData } from "@/components/work/work-structured-data";
import { ExpressionStructuredData } from "@/components/expression/expression-structured-data";
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

/**
 * Extracts and parses the JSON-LD from a rendered container.
 *
 * @param container - The rendered DOM container.
 * @returns The parsed JSON-LD object.
 */
function parseJsonLd(container: HTMLElement): Record<string, any> {
  const scriptTag = container.querySelector("script[type='application/ld+json']");
  expect(scriptTag).not.toBeNull();
  return JSON.parse(scriptTag!.textContent || "{}");
}

/**
 * Asserts the serialized JSON-LD source does not contain a literal closing script tag from input.
 *
 * @param container - The rendered DOM container.
 */
function assertNoScriptBreakout(container: HTMLElement) {
  const scriptTag = container.querySelector("script[type='application/ld+json']");
  expect(scriptTag).not.toBeNull();
  const html = scriptTag!.innerHTML;
  // The HTML-safe serializer must have escaped all < characters
  expect(html).not.toMatch(/<(?!\/)/); // no unescaped < except possibly closing tags
  // More importantly: no literal </script> sequence from input values
  // (the only </script> should be the actual closing tag of the element, not inside innerHTML)
  expect(html).not.toContain("</script>");
}

describe("SSR JSON-LD Safety: parsed values preserved with malicious inputs", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("manifestation page preserves title containing </script> through SSR JSON-LD", async () => {
    const maliciousTitle = '</script><script>alert("xss")</script>';
    const mockManifestation = {
      id: 2053,
      title: maliciousTitle,
      authors: ["Normal Author"],
      content_type: "book",
      meta: { Year: "2024" },
    };

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockManifestation }),
    } as unknown as Response);

    const pageJsx = await ManifestationPage({ params: Promise.resolve({ id: "2053" }) });
    const { container } = renderWithClient(pageJsx);

    assertNoScriptBreakout(container);
    const parsed = parseJsonLd(container);

    // The parsed JSON-LD must preserve the original malicious title
    expect(parsed["name"]).toBe(maliciousTitle);
    expect(parsed["@type"]).toBe("Book");
    expect(parsed["author"]["name"]).toBe("Normal Author");
  });

  it("shared collection page preserves description with HTML entities through SSR JSON-LD", async () => {
    const maliciousDescription = 'Items with <b>bold</b> & "quotes" and </script> breakout';
    const mockSharedCollection = {
      author: "Collector </script>",
      collection_name: "My <Special> Collection",
      collection_description: maliciousDescription,
      items: [{ id: 101, manifestation_id: 1996, title: "Item </script>", authors: ["Author & Friends"] }],
    };

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockSharedCollection }),
    } as unknown as Response);

    const pageJsx = await SharedCollectionPage({ params: Promise.resolve({ token: "test-token" }) });
    const { container } = renderWithClient(pageJsx);

    assertNoScriptBreakout(container);
    const parsed = parseJsonLd(container);

    expect(parsed["name"]).toBe("My <Special> Collection");
    expect(parsed["description"]).toBe(maliciousDescription);
    expect(parsed["author"]["name"]).toBe("Collector </script>");
    const itemList = (parsed["mainEntity"] as any).itemListElement;
    expect(itemList[0].item.name).toBe("Item </script>");
  });

  it("public profile page preserves bio with Unicode separators and multiline text", async () => {
    const maliciousBio = 'Line 1\u2028Line 2\u2029Line 3\n<b>bold</b> & "quoted" </script>';
    const mockProfile = {
      username: "evil_user",
      display_name: "Display </script>",
      bio: maliciousBio,
      avatar_url: "https://example.com/avatar.jpg",
    };

    vi.spyOn(global, "fetch").mockImplementation(async (url: any) => {
      const urlStr = String(url);
      if (urlStr.includes("/items")) {
        return {
          ok: true,
          json: async () => ({ success: true, data: { items: [] } }),
        } as unknown as Response;
      }
      return {
        ok: true,
        json: async () => ({ success: true, data: mockProfile }),
      } as unknown as Response;
    });

    const pageJsx = await PublicProfilePage({ params: Promise.resolve({ username: "evil_user" }) });
    const { container } = renderWithClient(pageJsx);

    assertNoScriptBreakout(container);
    const parsed = parseJsonLd(container);

    expect(parsed["name"]).toBe("Display </script>'s Library");
    const person = parsed["mainEntity"] as any;
    expect(person["name"]).toBe("Display </script>");
    expect(person["description"]).toBe(maliciousBio);
    expect(person["alternateName"]).toBe("evil_user");
  });

  it("item page preserves FRBR hierarchy with malicious work title", async () => {
    const maliciousTitle = "Dune </script><script>alert(1)</script>";
    const mockItem = {
      id: 55,
      title: maliciousTitle,
      authors: ["Frank </script>"],
      manifestation_id: 12,
      work: {
        id: 7,
        title: maliciousTitle,
        authors: ["Frank </script>"],
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

    assertNoScriptBreakout(container);
    const parsed = parseJsonLd(container);

    expect(parsed["name"]).toBe(maliciousTitle);
    expect(parsed["author"]["name"]).toBe("Frank </script>");
    expect(parsed["@type"]).toBe("CreativeWork");
  });

  it("WorkStructuredData component preserves malicious manifestation titles", () => {
    const { container } = render(
      <WorkStructuredData
        data={{
          id: 1,
          title: 'Work </script> & "quoted"',
          authors: ["Author <b>bold</b>"],
          manifestations: [
            {
              id: 10,
              title: "Manifestation </script>",
              isbn: "978-0-441-17271-9",
              language: "eng",
              contentType: "book",
              year: 1965,
            },
          ],
        }}
      />
    );

    assertNoScriptBreakout(container);
    const parsed = parseJsonLd(container);

    expect(parsed["name"]).toBe('Work </script> & "quoted"');
    expect(parsed["author"]["name"]).toBe("Author <b>bold</b>");
    const examples = parsed["workExample"] as any[];
    expect(examples[0].name).toBe("Manifestation </script>");
    expect(examples[0].isbn).toBe("978-0-441-17271-9");
  });

  it("ExpressionStructuredData component preserves malicious work title", () => {
    const { container } = render(
      <ExpressionStructuredData
        data={{
          id: 5,
          workId: 1,
          workTitle: 'Work </script> & "quoted"',
          authors: ["Author <b>bold</b>"],
          language: "eng",
          contentType: "text",
          manifestations: [
            {
              id: 10,
              title: "Manifestation </script>",
              contentType: "book",
            },
          ],
        }}
      />
    );

    assertNoScriptBreakout(container);
    const parsed = parseJsonLd(container);

    expect(parsed["name"]).toContain('Work </script> & "quoted"');
    expect(parsed["author"]["name"]).toBe("Author <b>bold</b>");
    expect(parsed["isPartOf"]["name"]).toBe('Work </script> & "quoted"');
  });

  it("collection layout preserves static JSON-LD fields (no user input, but verifies round-trip)", () => {
    const { container } = render(
      <CollectionLayout>
        <div>Catalog</div>
      </CollectionLayout>
    );

    const parsed = parseJsonLd(container);
    expect(parsed["@context"]).toBe("https://schema.org");
    expect(parsed["@type"]).toBe("CollectionPage");
    expect(parsed["name"]).toBe("iqoqo Library Collection");
    expect(parsed["description"]).toContain("Browse and discover");
  });
});
