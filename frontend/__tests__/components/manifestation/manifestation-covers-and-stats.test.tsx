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
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import enMessages from "@/messages/en.json";
import { ManifestationCoversGallery } from "@/components/manifestation/manifestation-covers-gallery";
import { ManifestationStatsCard } from "@/components/manifestation/manifestation-stats-card";
import type { ManifestationImage, ManifestationStats } from "@/types/frbr";

vi.mock("next-intl", () => ({
  useTranslations: (namespace?: string) => {
    const root = enMessages as unknown as Record<string, Record<string, string>>;
    const dictionary = namespace ? root[namespace] : {};
    return (key: string) => dictionary?.[key] ?? key;
  },
}));

vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ src, alt, ...props }: { src: string; alt: string }) => <img src={src} alt={alt} {...props} />,
}));

const mockUseManifestationImages = vi.fn<() => { data: ManifestationImage[] }>();
const mockUseManifestationStats = vi.fn<() => { data: ManifestationStats | undefined; isLoading: boolean }>();

vi.mock("@/lib/api/hooks/catalog", () => ({
  useManifestationImages: () => mockUseManifestationImages(),
  useManifestationStats: () => mockUseManifestationStats(),
}));

describe("ManifestationCoversGallery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("deduplicates primary cover, renders provenance badge, and opens/closes lightbox", () => {
    mockUseManifestationImages.mockReturnValue({
      data: [
        {
          id: 1,
          url: "https://covers.example.org/primary.jpg",
          label: "Primary",
          source: "openlibrary",
          added_at: null,
        },
        {
          id: 2,
          url: "https://covers.example.org/back-scan.jpg",
          label: "Back Cover Scan",
          source: "community",
          added_at: "2026-03-01T10:00:00Z",
        },
      ],
    });

    render(
      <ManifestationCoversGallery manifestationId={42} primaryCoverUrl="https://covers.example.org/primary.jpg" />
    );

    expect(screen.getByTestId("manifestation-covers-gallery")).toBeInTheDocument();
    expect(screen.queryByAltText("Primary")).not.toBeInTheDocument();
    expect(screen.getByAltText("Back Cover Scan")).toBeInTheDocument();
    expect(screen.getByText("community")).toBeInTheDocument();

    fireEvent.click(screen.getByAltText("Back Cover Scan").closest("button")!);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Close cover preview"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("ManifestationStatsCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders KPI pills and popularity chart when activity is present", () => {
    mockUseManifestationStats.mockReturnValue({
      isLoading: false,
      data: {
        manifestation_id: 42,
        total_items: 5,
        reader_count: 4,
        completed_count: 3,
        avg_session_minutes: 45.5,
        avg_reading_days: 7.0,
        popularity_over_time: [
          { month: "2026-02", added_count: 2, completed_count: 1 },
          { month: "2026-03", added_count: 3, completed_count: 2 },
        ],
      },
    });

    render(<ManifestationStatsCard manifestationId={42} />);

    expect(screen.getByTestId("manifestation-stats-card")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("45.5m")).toBeInTheDocument();
    expect(screen.getByText("7d")).toBeInTheDocument();
    expect(screen.getByTestId("popularity-chart")).toBeInTheDocument();
  });

  it("renders graceful empty state when manifestation has zero activity", () => {
    mockUseManifestationStats.mockReturnValue({
      isLoading: false,
      data: {
        manifestation_id: 42,
        total_items: 0,
        reader_count: 0,
        completed_count: 0,
        avg_session_minutes: null,
        avg_reading_days: null,
        popularity_over_time: [],
      },
    });

    render(<ManifestationStatsCard manifestationId={42} />);

    expect(screen.getByText("No community reading activity recorded yet.")).toBeInTheDocument();
    expect(screen.queryByTestId("popularity-chart")).not.toBeInTheDocument();
  });
});
