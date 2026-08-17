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

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => {
    const map: Record<string, string> = {
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
  useDistributionInsights: vi.fn(),
}));

import { useDistributionInsights } from "@/lib/api/hooks";
import { TypeDistributionChart } from "@/components/dashboard/type-distribution-chart";

const mockUseDistribution = vi.mocked(useDistributionInsights);

describe("TypeDistributionChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton while loading", () => {
    mockUseDistribution.mockReturnValue({ data: undefined, isLoading: true, isError: false } as ReturnType<
      typeof useDistributionInsights
    >);
    render(<TypeDistributionChart />);
    expect(screen.getByTestId("distribution-chart-skeleton")).toBeInTheDocument();
  });

  it("renders error state on query error", () => {
    mockUseDistribution.mockReturnValue({ data: undefined, isLoading: false, isError: true } as ReturnType<
      typeof useDistributionInsights
    >);
    render(<TypeDistributionChart />);
    expect(screen.getByTestId("distribution-chart-error")).toBeInTheDocument();
  });

  it("renders chart component and toggles between type and format tabs", () => {
    const mockData = {
      by_type: [
        { type: "text", count: 12 },
        { type: "music", count: 4 },
      ],
      by_format: [
        { format: "book", count: 12 },
        { format: "cd", count: 4 },
      ],
    };
    mockUseDistribution.mockReturnValue({ data: mockData, isLoading: false, isError: false } as ReturnType<
      typeof useDistributionInsights
    >);
    render(<TypeDistributionChart />);
    expect(screen.getByTestId("type-distribution-chart")).toBeInTheDocument();
    expect(screen.getByText("Collection Distribution")).toBeInTheDocument();

    const byFormatBtn = screen.getByText("By Format");
    fireEvent.click(byFormatBtn);
    expect(byFormatBtn).toHaveClass("bg-card");
  });

  // ── 6.4 Empty data arrays ─────────────────────────────────────────────
  it("renders empty state when data has empty arrays", () => {
    mockUseDistribution.mockReturnValue({
      data: { by_type: [], by_format: [] },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDistributionInsights>);
    render(<TypeDistributionChart />);

    // Should show the empty state text
    expect(screen.getByTestId("type-distribution-chart")).toBeInTheDocument();
    expect(screen.getByText("No collection items cataloged yet.")).toBeInTheDocument();
  });

  it("passes scope prop to useDistributionInsights hook", () => {
    mockUseDistribution.mockReturnValue({
      data: { by_type: [], by_format: [] },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDistributionInsights>);
    render(<TypeDistributionChart scope="global" />);
    expect(mockUseDistribution).toHaveBeenCalledWith("global");
  });
});
