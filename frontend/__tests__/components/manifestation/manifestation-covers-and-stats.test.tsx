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
import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import enMessages from "@/messages/en.json";
import { apiClient } from "@/lib/api/client";
import { ManifestationCoversGallery } from "@/components/manifestation/manifestation-covers-gallery";
import { ManifestationStatsCard } from "@/components/manifestation/manifestation-stats-card";

vi.mock("next-intl", () => ({
  useTranslations: (namespace?: string) => {
    const root = enMessages as unknown as Record<string, Record<string, string>>;
    const dictionary = namespace ? root[namespace] : {};
    return (key: string) => dictionary?.[key] ?? key;
  },
}));

vi.mock("next/image", () => ({
  default: ({ src, alt, className }: { src: string; alt: string; className?: string }) =>
    React.createElement("span", { role: "img", "aria-label": alt, "data-src": src, className }),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

const renderWithQuery = (ui: React.ReactElement) => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
};

describe("ManifestationCoversGallery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads images via real useManifestationImages hook, deduplicates primary, and handles lightbox open/close", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        success: true,
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
      },
    });

    renderWithQuery(
      <ManifestationCoversGallery manifestationId={42} primaryCoverUrl="https://covers.example.org/primary.jpg" />
    );

    await waitFor(() => {
      expect(screen.getByRole("img", { name: "Back Cover Scan" })).toBeInTheDocument();
    });
    expect(screen.queryByRole("img", { name: "Primary" })).not.toBeInTheDocument();
    expect(screen.getByText("community")).toBeInTheDocument();
    expect(apiClient.get).toHaveBeenCalledWith("/manifestations/42/images");

    await user.click(screen.getByRole("button", { name: /community/i }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close cover preview" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    // Backdrop click also closes dialog
    await user.click(screen.getByRole("button", { name: /community/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByRole("dialog"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("closes the cover lightbox preview when pressing Escape", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        success: true,
        data: [
          {
            id: 2,
            url: "https://covers.example.org/back-scan.jpg",
            label: "Back Cover Scan",
            source: "community",
            added_at: "2026-03-01T10:00:00Z",
          },
        ],
      },
    });

    renderWithQuery(<ManifestationCoversGallery manifestationId={42} />);
    await waitFor(() => {
      expect(screen.getByRole("img", { name: "Back Cover Scan" })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /community/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders nothing when all contributed images duplicate the primary cover", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        success: true,
        data: [
          {
            id: 1,
            url: "https://covers.example.org/primary.jpg",
            label: "Primary",
            source: "openlibrary",
            added_at: null,
          },
        ],
      },
    });

    const { container } = renderWithQuery(
      <ManifestationCoversGallery manifestationId={43} primaryCoverUrl="https://covers.example.org/primary.jpg" />
    );

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith("/manifestations/43/images");
    });
    expect(container).toBeEmptyDOMElement();
  });
});

describe("ManifestationStatsCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads KPIs and popularity timeline via real useManifestationStats hook", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        success: true,
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
      },
    });

    renderWithQuery(<ManifestationStatsCard manifestationId={42} />);

    await waitFor(() => {
      expect(screen.getByText("Reading Activity & Popularity")).toBeInTheDocument();
    });
    expect(apiClient.get).toHaveBeenCalledWith("/manifestations/42/stats");
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("45.5m")).toBeInTheDocument();
    expect(screen.getByText("7d")).toBeInTheDocument();
    expect(screen.getByText("Popularity Over Time")).toBeInTheDocument();
  });

  it("renders graceful empty state when manifestation has zero activity", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          manifestation_id: 42,
          total_items: 0,
          reader_count: 0,
          completed_count: 0,
          avg_session_minutes: null,
          avg_reading_days: null,
          popularity_over_time: [],
        },
      },
    });

    renderWithQuery(<ManifestationStatsCard manifestationId={42} />);

    await waitFor(() => {
      expect(screen.getByText("No community reading activity recorded yet.")).toBeInTheDocument();
    });
    expect(screen.queryByText("Popularity Over Time")).not.toBeInTheDocument();
  });
});
