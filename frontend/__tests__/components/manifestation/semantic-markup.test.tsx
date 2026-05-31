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
import { describe, it, expect, vi } from "vitest";
import ManifestationPage from "@/app/manifestation/[id]/page";
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

  it("should inject a valid application/ld+json script for AI agent search engines", () => {
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as any);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({ data: mockManifestation, isLoading: false } as any);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as any);

    const { container } = renderWithQueryClient(<ManifestationPage />);

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
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as any);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({ data: mockManifestation, isLoading: false } as any);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as any);

    const { container } = renderWithQueryClient(<ManifestationPage />);

    const mainContainer = container.firstChild as HTMLElement;
    expect(mainContainer).toBeInTheDocument();
    expect(mainContainer.getAttribute("vocab")).toBe("http://iflastandards.info/ns/frbr/frbrer/");
    expect(mainContainer.getAttribute("typeof")).toBe("Manifestation");
    expect(mainContainer.getAttribute("resource")).toBe("#manifestation-123");

    const workLink = container.querySelector("a[rel='embodimentOf']");
    expect(workLink).toBeInTheDocument();
    expect(workLink?.getAttribute("href")).toBe("/api/public/works/456");
  });

  it("should render SIOC topic elements for automated folksonomy categorization mapping", () => {
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as any);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({ data: mockManifestation, isLoading: false } as any);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as any);

    renderWithQueryClient(<ManifestationPage />);

    const classicTag = screen.getByText("Classic");
    const fantasyTag = screen.getByText("Fantasy");

    expect(classicTag).toBeInTheDocument();
    expect(classicTag.getAttribute("property")).toBe("sioc:topic");

    expect(fantasyTag).toBeInTheDocument();
    expect(fantasyTag.getAttribute("property")).toBe("sioc:topic");
  });

  it("should map content_type to correct Schema.org type for music", () => {
    const musicManifestation = {
      ...mockManifestation,
      id: 200,
      title: "Abbey Road",
      content_type: "music",
      authors: ["The Beatles"],
    };
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as any);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({ data: musicManifestation, isLoading: false } as any);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as any);

    const { container } = renderWithQueryClient(<ManifestationPage />);
    const scriptTag = container.querySelector("script[type='application/ld+json']");
    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@type"]).toBe("MusicAlbum");
  });

  it("should map content_type to correct Schema.org type for movie", () => {
    const movieManifestation = {
      ...mockManifestation,
      id: 201,
      title: "Inception",
      content_type: "movie",
      authors: ["Christopher Nolan"],
    };
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as any);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({ data: movieManifestation, isLoading: false } as any);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as any);

    const { container } = renderWithQueryClient(<ManifestationPage />);
    const scriptTag = container.querySelector("script[type='application/ld+json']");
    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@type"]).toBe("Movie");
  });

  it("should map content_type to correct Schema.org type for puzzle", () => {
    const puzzleManifestation = {
      ...mockManifestation,
      id: 202,
      title: "Ravensburger 1000pc",
      content_type: "puzzle",
      authors: [],
    };
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as any);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({ data: puzzleManifestation, isLoading: false } as any);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as any);

    const { container } = renderWithQueryClient(<ManifestationPage />);
    const scriptTag = container.querySelector("script[type='application/ld+json']");
    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@type"]).toBe("Product");
  });

  it("should include inLanguage in JSON-LD when available", () => {
    const langManifestation = {
      ...mockManifestation,
      meta: { ...mockManifestation.meta, language: "en" },
    };
    vi.spyOn(hooks, "useProfile").mockReturnValue({ data: { id: 1 } } as any);
    vi.spyOn(hooks, "useManifestation").mockReturnValue({ data: langManifestation, isLoading: false } as any);
    vi.spyOn(hooks, "useWorkParts").mockReturnValue({ data: [], isLoading: false } as any);

    const { container } = renderWithQueryClient(<ManifestationPage />);
    const scriptTag = container.querySelector("script[type='application/ld+json']");
    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["inLanguage"]).toBe("en");
  });
});
