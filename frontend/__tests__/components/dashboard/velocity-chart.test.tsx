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
      velocityTitle: "Acquisition Velocity",
      velocityDesc: "Items cataloged per month over the past 12 months",
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
  useVelocityInsights: vi.fn(),
}));

import { useVelocityInsights } from "@/lib/api/hooks";
import { VelocityChart } from "@/components/dashboard/velocity-chart";

const mockUseVelocity = vi.mocked(useVelocityInsights);

describe("VelocityChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton while loading", () => {
    mockUseVelocity.mockReturnValue({ data: undefined, isLoading: true, isError: false } as ReturnType<
      typeof useVelocityInsights
    >);
    render(<VelocityChart />);
    expect(screen.getByTestId("velocity-chart-skeleton")).toBeInTheDocument();
  });

  it("renders error state on query error", () => {
    mockUseVelocity.mockReturnValue({ data: undefined, isLoading: false, isError: true } as ReturnType<
      typeof useVelocityInsights
    >);
    render(<VelocityChart />);
    expect(screen.getByTestId("velocity-chart-error")).toBeInTheDocument();
  });

  it("renders chart component with acquisition data", () => {
    const mockData = [
      { month: "2026-01", count: 3 },
      { month: "2026-02", count: 5 },
    ];
    mockUseVelocity.mockReturnValue({ data: mockData, isLoading: false, isError: false } as ReturnType<
      typeof useVelocityInsights
    >);
    render(<VelocityChart />);
    expect(screen.getByTestId("velocity-chart")).toBeInTheDocument();
    expect(screen.getByText("Acquisition Velocity")).toBeInTheDocument();
  });
});
