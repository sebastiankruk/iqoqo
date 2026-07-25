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

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const map: Record<string, string> = {
      title: "Collector Insights",
      subtitle: "Temporal acquisition patterns and collection breakdown",
      velocityTitle: "Acquisition Velocity",
      velocityDesc: "Items cataloged per month over the past 12 months",
      distributionTitle: "Collection Distribution",
      distributionDesc: "Breakdown by content type and physical format",
      byType: "By Content Type",
      byFormat: "By Format",
      emptyState: "No collection items cataloged yet.",
    };
    return map[key] || key;
  },
}));

vi.mock("recharts", async () => {
  const original = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...original,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 500, height: 300 }}>{children}</div>
    ),
  };
});

vi.mock("@/lib/api/hooks", () => ({
  useStats: vi.fn(),
  useVelocityInsights: vi.fn(),
  useDistributionInsights: vi.fn(),
}));

import { useStats, useVelocityInsights, useDistributionInsights } from "@/lib/api/hooks";
import { CollectionInsights } from "@/components/dashboard/collection-insights";

const mockUseStats = vi.mocked(useStats);
const mockUseVelocity = vi.mocked(useVelocityInsights);
const mockUseDistribution = vi.mocked(useDistributionInsights);

describe("CollectionInsights", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseStats.mockReturnValue({
      data: { total_items: 5 },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useStats>);
  });

  it("renders both VelocityChart and TypeDistributionChart components", () => {
    mockUseVelocity.mockReturnValue({
      data: [{ month: "2026-01", count: 2 }],
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useVelocityInsights>);

    mockUseDistribution.mockReturnValue({
      data: { by_type: [{ type: "text", count: 2 }], by_format: [{ format: "book", count: 2 }] },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDistributionInsights>);

    render(<CollectionInsights />);
    expect(screen.getByTestId("collection-insights")).toBeInTheDocument();
    expect(screen.getByTestId("velocity-chart")).toBeInTheDocument();
    expect(screen.getByTestId("type-distribution-chart")).toBeInTheDocument();
  });

  it("isolates errors so failure in one chart does not crash the other", () => {
    mockUseVelocity.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useVelocityInsights>);

    mockUseDistribution.mockReturnValue({
      data: { by_type: [{ type: "text", count: 2 }], by_format: [{ format: "book", count: 2 }] },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useDistributionInsights>);

    render(<CollectionInsights />);
    expect(screen.getByTestId("velocity-chart-error")).toBeInTheDocument();
    expect(screen.getByTestId("type-distribution-chart")).toBeInTheDocument();
  });

  it("does not render stats charts section when total_items is 0", () => {
    mockUseStats.mockReturnValue({
      data: { total_items: 0 },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useStats>);

    render(<CollectionInsights />);
    expect(screen.queryByTestId("collection-insights")).not.toBeInTheDocument();
  });

  it("renders collection-insights section during loading", () => {
    mockUseStats.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useStats>);

    mockUseVelocity.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useVelocityInsights>);

    mockUseDistribution.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useDistributionInsights>);

    render(<CollectionInsights />);
    // Section should render even when loading (stats undefined means it doesn't return null)
    expect(screen.getByTestId("collection-insights")).toBeInTheDocument();
  });

  it("renders collection-insights section on error", () => {
    mockUseStats.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useStats>);

    mockUseVelocity.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useVelocityInsights>);

    mockUseDistribution.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useDistributionInsights>);

    render(<CollectionInsights />);
    // Section should render even on error (stats undefined means it doesn't return null)
    expect(screen.getByTestId("collection-insights")).toBeInTheDocument();
  });
});
