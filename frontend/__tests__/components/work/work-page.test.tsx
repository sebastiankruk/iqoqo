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
import WorkPage, { generateMetadata as generateWorkMetadata } from "@/app/work/[id]/page";
import ExpressionPage, { generateMetadata as generateExpressionMetadata } from "@/app/expression/[id]/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useParams: () => ({ id: "1993" }),
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => ({
    get: () => null,
  }),
  notFound: vi.fn(),
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

describe("WorkPage & ExpressionPage Semantic Web Validation", () => {
  const mockWork = {
    id: 1993,
    title: "The Singles 1992 - 2003",
    authors: ["No Doubt"],
    meta: { authors: ["No Doubt"] },
    expressions: [
      {
        id: 2062,
        work_id: 1993,
        content_type: "music",
        language: "en",
        kind: null,
        is_live_performance: false,
        manifestations: [
          {
            id: 2053,
            expression_id: 2062,
            work_id: 1993,
            title: "The Singles 1992 - 2003",
            isbn13: "602498613818",
            publisher: "Interscope Records",
            format: "cd",
            format_type: "cd",
            year: 2003,
            cover_url: "https://example.com/cover.jpg",
          },
        ],
      },
    ],
  };

  const mockExpression = {
    id: 2062,
    work_id: 1993,
    work_title: "The Singles 1992 - 2003",
    authors: ["No Doubt"],
    content_type: "music",
    language: "en",
    kind: null,
    is_live_performance: false,
    manifestations: [
      {
        id: 2053,
        expression_id: 2062,
        work_id: 1993,
        title: "The Singles 1992 - 2003",
        isbn13: "602498613818",
        publisher: "Interscope Records",
        format: "cd",
        format_type: "cd",
        year: 2003,
        cover_url: "https://example.com/cover.jpg",
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/works/1993")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockWork }),
        });
      }
      if (url.includes("/expressions/2062")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: mockExpression }),
        });
      }
      return Promise.resolve({ ok: false });
    });
  });

  it("should render WorkPage with CreativeWork JSON-LD and Microdata in SSR", async () => {
    const page = await WorkPage({ params: Promise.resolve({ id: "1993" }) });
    const { container } = renderWithQueryClient(page);

    // Verify JSON-LD script
    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();
    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(jsonLd["@type"]).toBe("CreativeWork");
    expect(jsonLd["name"]).toBe("The Singles 1992 - 2003");
    expect(jsonLd["workExample"]).toHaveLength(1);
    expect(jsonLd["workExample"][0]["identifier"]).toBe(2053);

    // Verify Microdata in DOM
    const workMain = container.querySelector("main[itemtype='https://schema.org/CreativeWork']");
    expect(workMain).toBeInTheDocument();
    expect(container.querySelector("[itemprop='name']")?.textContent).toBe("The Singles 1992 - 2003");
  });

  it("should generate SEO metadata for WorkPage pointing to public JSON-LD endpoint", async () => {
    const metadata = await generateWorkMetadata({ params: Promise.resolve({ id: "1993" }) });
    expect(metadata.title).toBe("The Singles 1992 - 2003 - iqoqo");
    expect(metadata.alternates?.types?.["application/ld+json"]).toBeDefined();
    const ldJsonRef = (metadata.alternates?.types?.["application/ld+json"] as any[])[0];
    expect(ldJsonRef.url).toBe("/api/public/works/1993");
  });

  it("should render ExpressionPage with CreativeWork JSON-LD linking to parent Work", async () => {
    const page = await ExpressionPage({ params: Promise.resolve({ id: "2062" }) });
    const { container } = renderWithQueryClient(page);

    const scriptTag = container.querySelector("script[type='application/ld+json']");
    expect(scriptTag).not.toBeNull();
    const jsonLd = JSON.parse(scriptTag!.textContent || "{}");
    expect(jsonLd["@type"]).toBe("CreativeWork");
    expect(jsonLd["isPartOf"]["identifier"]).toBe(1993);
    expect(jsonLd["isPartOf"]["url"]).toBe("/work/1993");

    // Verify link to work in DOM
    const workLink = container.querySelector("a[rel='expressionOf']");
    expect(workLink).toBeInTheDocument();
    expect(workLink?.getAttribute("href")).toBe("/work/1993");
  });

  it("should generate SEO metadata for ExpressionPage pointing to public JSON-LD endpoint", async () => {
    const metadata = await generateExpressionMetadata({ params: Promise.resolve({ id: "2062" }) });
    expect(metadata.alternates?.types?.["application/ld+json"]).toBeDefined();
    const ldJsonRef = (metadata.alternates?.types?.["application/ld+json"] as any[])[0];
    expect(ldJsonRef.url).toBe("/api/public/expressions/2062");
  });
});
