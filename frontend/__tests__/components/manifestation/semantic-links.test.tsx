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

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SemanticLinks } from "@/components/manifestation/semantic-links";
import * as hooks from "@/lib/api/hooks";
import type { SemanticLink } from "@/types/frbr";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    const map: Record<string, string> = {
      title: "Linked Open Data",
      description: "External semantic knowledge graph links connected to this work and edition.",
      scanButton: "Scan External LOD",
      scanning: "Scanning LOD...",
      scanStarted: "LOD background reconciliation scheduled.",
      noLinks: "No external Linked Open Data authorities linked yet.",
      noLinksHint: "Scan external authorities to enrich with DBpedia, GeoNames, and WordNet entities.",
      verified: "Verified",
      unverified: "Auto-matched",
      deleteLink: "Remove link",
      linkDeleted: "Semantic link removed.",
      "levels.work": "Work Level",
      "levels.manifestation": "Edition Level",
    };
    if (key === "confidence" && params?.score !== undefined) {
      return `${params.score}% confidence`;
    }
    return map[key] || key;
  },
}));

vi.mock("@/lib/api/hooks", () => ({
  useSemanticLinks: vi.fn(),
  useTriggerRelink: vi.fn(),
  useDeleteSemanticLink: vi.fn(),
}));

describe("SemanticLinks Component", () => {
  const mockRelinkMutate = vi.fn();
  const mockDeleteMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(hooks.useTriggerRelink).mockReturnValue({
      mutate: mockRelinkMutate,
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useTriggerRelink>);

    vi.mocked(hooks.useDeleteSemanticLink).mockReturnValue({
      mutate: mockDeleteMutate,
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useDeleteSemanticLink>);
  });

  it("renders loading skeleton when fetching links", () => {
    vi.mocked(hooks.useSemanticLinks).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof hooks.useSemanticLinks>);

    const { container } = render(<SemanticLinks manifestationId={1} />);
    expect(screen.getByText("Linked Open Data")).toBeInTheDocument();
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("renders empty state when no links exist", () => {
    vi.mocked(hooks.useSemanticLinks).mockReturnValue({
      data: { manifestation_id: 1, total: 0, links: [], grouped: {} },
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useSemanticLinks>);

    render(<SemanticLinks manifestationId={1} />);
    expect(screen.getByText("No external Linked Open Data authorities linked yet.")).toBeInTheDocument();
    expect(screen.getByText("Scan External LOD")).toBeInTheDocument();
  });

  it("triggers LOD relink on scan button click", () => {
    vi.mocked(hooks.useSemanticLinks).mockReturnValue({
      data: { manifestation_id: 1, total: 0, links: [], grouped: {} },
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useSemanticLinks>);

    render(<SemanticLinks manifestationId={1} />);
    const scanBtn = screen.getByRole("button", { name: /scan external lod/i });
    expect(scanBtn).toHaveClass("whitespace-nowrap");
    expect(scanBtn).toHaveAttribute("title", "Scan External LOD");
    fireEvent.click(scanBtn);
    expect(mockRelinkMutate).toHaveBeenCalledTimes(1);
  });

  it("renders resolved links with authority badges, confidence, and secure target=_blank", () => {
    const mockLinks: SemanticLink[] = [
      {
        id: 101,
        entity_type: "work",
        entity_id: 1,
        authority: "dbpedia",
        external_uri: "http://dbpedia.org/resource/The_Hobbit",
        pref_label: "The Hobbit",
        confidence: 0.98,
        verified: true,
      },
      {
        id: 102,
        entity_type: "manifestation",
        entity_id: 2,
        authority: "geonames",
        external_uri: "https://sws.geonames.org/2643743/",
        pref_label: "London",
        confidence: 0.92,
        verified: false,
      },
    ];

    vi.mocked(hooks.useSemanticLinks).mockReturnValue({
      data: {
        manifestation_id: 2,
        total: 2,
        links: mockLinks,
        grouped: { dbpedia: [mockLinks[0]], geonames: [mockLinks[1]] },
      },
      isLoading: false,
    } as unknown as ReturnType<typeof hooks.useSemanticLinks>);

    render(<SemanticLinks manifestationId={2} canEdit={true} />);

    // Check authority badges
    expect(screen.getByText("DBpedia")).toBeInTheDocument();
    expect(screen.getByText("GeoNames")).toBeInTheDocument();

    // Check labels
    expect(screen.getByText("The Hobbit")).toBeInTheDocument();
    expect(screen.getByText("London")).toBeInTheDocument();

    // Check confidence scores
    expect(screen.getByText("98% confidence")).toBeInTheDocument();
    expect(screen.getByText("92% confidence")).toBeInTheDocument();

    // Check verified badge
    expect(screen.getByText("Verified")).toBeInTheDocument();

    // Check external link attributes (target=_blank and rel=noopener noreferrer)
    const hobbitLink = screen.getByRole("link", { name: /the hobbit/i });
    expect(hobbitLink).toHaveAttribute("href", "http://dbpedia.org/resource/The_Hobbit");
    expect(hobbitLink).toHaveAttribute("target", "_blank");
    expect(hobbitLink).toHaveAttribute("rel", "noopener noreferrer");

    // Check delete button interaction
    const deleteButtons = screen.getAllByRole("button", { name: "Remove link" });
    expect(deleteButtons.length).toBe(2);
    fireEvent.click(deleteButtons[0]);
    expect(mockDeleteMutate).toHaveBeenCalledWith(101, expect.any(Object));
  });
});
