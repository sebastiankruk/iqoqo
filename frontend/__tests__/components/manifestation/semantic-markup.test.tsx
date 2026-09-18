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
import ManifestationPage, { generateMetadata } from "@/app/manifestation/[id]/page";
import { ManifestationDetailClient } from "@/components/manifestation/manifestation-detail-client";
import * as hooks from "@/lib/api/hooks";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useParams: () => ({ id: "123" }),
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
  useSearchParams: () => ({
    get: () => null,
  }),
}));

vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
  default: (props: React.ComponentProps<"img">) => <img {...props} />,
}));

const createTestQueryClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

const renderWithQueryClient = (component: React.ReactElement) => {
  const testQueryClient = createTestQueryClient();
  return render(<QueryClientProvider client={testQueryClient}>{component}</QueryClientProvider>);
};

describe("Semantic Web Validation for Manifestation View", () => {
  const mockManifestation = {
    id: 123,
    title: "The Fellowship of the Ring",
    authors: ["J.R.R. Tolkien"],
    isbn13: "9780261102354",
    work_id: 456,
    expression_id: 789,
    content_type: "book",
    meta: {
      Publisher: "Allen & Unwin",
      Year: "1954",
      genres: ["Classic", "Fantasy"],
    },
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("should generate proper SEO metadata for manifestation in SSR", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockManifestation }),
    } as unknown as Response);

    const meta = await generateMetadata({ params: Promise.resolve({ id: "123" }) });
    expect(meta.title).toBe("The Fellowship of the Ring - iqoqo");
    expect(meta.description).toContain("J.R.R. Tolkien");
  });

  it("should inject a valid application/ld+json script for AI agent search engines in Server Component SSR", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: mockManifestation }),
    } as unknown as Response);
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as unknown as ReturnType<
      typeof hooks.useProfile
    >);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({
      data: mockManifestation,
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useManifestation>);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof hooks.useWorkParts
    >);

    const pageElement = await ManifestationPage({ params: Promise.resolve({ id: "123" }) });
    const { container } = renderWithQueryClient(pageElement);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).toBeInTheDocument();
    expect(scriptTag).not.toBeNull();

    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(jsonLd["@type"]).toBe("Book");
    expect(jsonLd["name"]).toBe("The Fellowship of the Ring");
    expect(jsonLd["author"]["name"]).toBe("J.R.R. Tolkien");
    expect(jsonLd["isbn"]).toBe("9780261102354");
  });

  it("should expose valid RDFa semantic attributes compliant with FRBRer ontology", () => {
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as unknown as ReturnType<
      typeof hooks.useProfile
    >);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({
      data: mockManifestation,
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useManifestation>);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof hooks.useWorkParts
    >);

    const { container } = renderWithQueryClient(
      <ManifestationDetailClient manifestationId={123} initialManifestation={mockManifestation as any} />
    );

    const mainContainer = container.firstChild as HTMLElement;
    expect(mainContainer).toBeInTheDocument();
    expect(mainContainer.getAttribute("vocab")).toBe("http://iflastandards.info/ns/frbr/frbrer/");
    expect(mainContainer.getAttribute("typeof")).toBe("Manifestation");
    expect(mainContainer.getAttribute("resource")).toBe("#manifestation-123");

    const workLink = container.querySelector("a[rel='embodimentOf']");
    expect(workLink).toBeInTheDocument();
    expect(workLink?.getAttribute("href")).toBe("/work/456");
  });

  it("should properly structure inLanguage and inventory item availability offers", async () => {
    const ownedManifestation = {
      ...mockManifestation,
      user_owns: true,
      meta: {
        ...mockManifestation.meta,
        language: "eng",
      },
    };

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: ownedManifestation }),
    } as unknown as Response);
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as unknown as ReturnType<
      typeof hooks.useProfile
    >);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({
      data: ownedManifestation,
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useManifestation>);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof hooks.useWorkParts
    >);

    const pageElement = await ManifestationPage({ params: Promise.resolve({ id: "123" }) });
    const { container } = renderWithQueryClient(pageElement);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();

    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["inLanguage"]).toBe("en");
    expect(Array.isArray(jsonLd["offers"])).toBe(true);
    expect(jsonLd["offers"][0]["availability"]).toBe("https://schema.org/InStock");
  });

  it("should map offers to PreOrder for wishlist items and resolve board_game schema type", async () => {
    const wishlistGame = {
      id: 999,
      title: "Catan",
      authors: ["Klaus Teuber"],
      content_type: "board_game",
      wishlist_item_id: 42,
      user_owns: false,
      meta: {
        Publisher: "Kosmos",
        Year: "1995",
        language: "deu",
      },
    };

    vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, data: wishlistGame }),
    } as unknown as Response);
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as unknown as ReturnType<
      typeof hooks.useProfile
    >);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({
      data: wishlistGame,
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useManifestation>);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as unknown as ReturnType<
      typeof hooks.useWorkParts
    >);

    const pageElement = await ManifestationPage({ params: Promise.resolve({ id: "999" }) });
    const { container } = renderWithQueryClient(pageElement);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();

    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@type"]).toBe("Game");
    expect(jsonLd["inLanguage"]).toBe("de");
    expect(jsonLd["offers"][0]["availability"]).toBe("https://schema.org/PreOrder");
  });
});
