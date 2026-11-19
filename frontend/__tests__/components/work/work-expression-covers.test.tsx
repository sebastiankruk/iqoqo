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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import enMessages from "@/messages/en.json";
import { ExpressionDetailClient } from "@/components/expression/expression-detail-client";
import { WorkDetailClient } from "@/components/work/work-detail-client";
import type { ExpressionDetail, WorkDetail } from "@/types/frbr";

const mockUseWork = vi.fn();
const mockUseExpression = vi.fn();
const mockUseProfile = vi.fn();

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

vi.mock("next-intl", () => ({
  useTranslations: (ns?: string) => (key: string, values?: Record<string, unknown>) => {
    const bucket = (enMessages as unknown as Record<string, Record<string, string>>)[ns ?? ""] ?? {};
    let template = bucket[key] ?? key;
    if (values) {
      for (const [k, v] of Object.entries(values)) {
        template = template.replaceAll(`{${k}}`, String(v));
      }
    }
    return template;
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ back: vi.fn(), push: vi.fn() }),
  useParams: () => ({ id: "2142" }),
}));

vi.mock("@/lib/api/hooks", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks")>();
  return {
    ...actual,
    useWork: () => mockUseWork(),
    useExpression: () => mockUseExpression(),
    useProfile: () => mockUseProfile(),
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

/** Render a component wrapped in a fresh non-retrying QueryClientProvider. */
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("WorkDetailClient and ExpressionDetailClient direct cover rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: { id: "user-1", username: "reader" } });
  });

  it("renders direct /static/covers URLs without /_next/image rewriting on WorkDetailClient", () => {
    const work: WorkDetail = {
      id: 2142,
      title: "Kalendarz adwentowy",
      authors: ["Story House Egmont"],
      expressions: [
        {
          id: 99,
          work_id: 2142,
          content_type: "text",
          language: "pl",
          manifestations: [
            {
              id: 500,
              cover_url: "/static/covers/kalendarz.jpg",
              format: "book",
              meta: {},
            },
          ],
        },
      ],
    };
    mockUseWork.mockReturnValue({ data: work, isLoading: false });

    renderWithQuery(<WorkDetailClient workId={2142} initialWork={work} />);

    const imgs = screen.getAllByAltText("Kalendarz adwentowy") as HTMLImageElement[];
    expect(imgs.length).toBeGreaterThanOrEqual(2);
    for (const img of imgs) {
      const src = img.getAttribute("src") ?? "";
      expect(src).toBe("/api/static/covers/kalendarz.jpg");
      expect(src).not.toContain("/_next/image");
    }
  });

  it("renders direct /static/covers URLs without /_next/image rewriting on ExpressionDetailClient", () => {
    const expr: ExpressionDetail = {
      id: 99,
      work_id: 2142,
      work_title: "Kalendarz adwentowy",
      authors: ["Story House Egmont"],
      content_type: "text",
      language: "pl",
      manifestations: [
        {
          id: 500,
          cover_url: "/static/covers/kalendarz.jpg",
          format: "book",
          meta: {},
        },
      ],
    };
    mockUseExpression.mockReturnValue({ data: expr, isLoading: false });

    renderWithQuery(<ExpressionDetailClient expressionId={99} initialExpression={expr} />);

    const imgs = screen.getAllByAltText("Kalendarz adwentowy") as HTMLImageElement[];
    expect(imgs.length).toBeGreaterThanOrEqual(2);
    for (const img of imgs) {
      const src = img.getAttribute("src") ?? "";
      expect(src).toBe("/api/static/covers/kalendarz.jpg");
      expect(src).not.toContain("/_next/image");
    }
  });
});
