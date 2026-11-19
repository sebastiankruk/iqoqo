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
import { ManifestationDetailClient } from "@/components/manifestation/manifestation-detail-client";
import { WorkDetailClient } from "@/components/work/work-detail-client";
import { WorkRollupBadge } from "@/components/work/work-rollup-badge";
import type { CatalogEntry, WorkDetail } from "@/types/frbr";

const mockUseWork = vi.fn();
const mockUseManifestation = vi.fn();
const mockUseProfile = vi.fn();

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

vi.mock("@/components/manifestation/manifestation-actions", () => ({
  ManifestationActions: () => null,
}));

vi.mock("@/components/manifestation/semantic-links", () => ({
  SemanticLinks: () => null,
}));

vi.mock("@/components/social/frbr-feedback", () => ({
  FRBRFeedback: () => null,
}));

vi.mock("@/components/item/extended-metadata", () => ({
  ExtendedMetadata: () => null,
}));

vi.mock("@/components/cover/cover-provenance", () => ({
  CoverProvenance: () => null,
}));

vi.mock("next-intl", () => ({
  useTranslations: (ns?: string) => (key: string, params?: Record<string, string>) => {
    const table = (enMessages as unknown as Record<string, Record<string, string>>)[ns || "WorkRollup"] || {};
    let template = table[key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        template = template.replace(`{${k}}`, v);
      }
    }
    return template;
  },
}));

vi.mock("@/lib/api/hooks", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks")>();
  return {
    ...actual,
    useWork: (id: number, initial?: WorkDetail | null) => mockUseWork(id, initial),
    useManifestation: (id: number, initial?: CatalogEntry | null) => mockUseManifestation(id, initial),
    useProfile: () => mockUseProfile(),
    useWorkParts: () => ({ data: [] }),
    useUserCollections: () => ({ data: [] }),
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

describe("C130 Work-Level Reading Status Rollup UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: { id: "user-1", username: "reader" } });
  });

  it("renders nothing when work_reading_status is null", () => {
    const { container } = render(<WorkRollupBadge status={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders Work reading rollup badge on WorkDetailClient", () => {
    const work: WorkDetail = {
      id: 42,
      title: "Solaris",
      authors: ["Stanislaw Lem"],
      expressions: [],
      work_reading_status: "reading",
      completed_manifestation_ids: [],
    };
    mockUseWork.mockReturnValue({ data: work, isLoading: false });

    renderWithQuery(<WorkDetailClient workId={42} initialWork={work} />);
    expect(screen.getByTestId("work-rollup-badge").textContent).toBe("Currently Reading");
  });

  it("renders 'Read (another edition)' badge on ManifestationDetailClient when completed_via_other_edition is true", () => {
    const manif: CatalogEntry = {
      id: 101,
      expression_id: 22,
      work_id: 42,
      title: "Solaris (Hardcover)",
      authors: ["Stanislaw Lem"],
      user_owns: false,
      meta: { format: "book" },
      work_reading_status: "read",
      completed_manifestation_ids: [88],
      completed_via_other_edition: true,
    };
    mockUseManifestation.mockReturnValue({ data: manif, isLoading: false, error: null });

    renderWithQuery(<ManifestationDetailClient manifestationId={101} initialManifestation={manif} />);
    expect(screen.getByTestId("work-rollup-badge").textContent).toBe("Read (another edition)");
  });
});
