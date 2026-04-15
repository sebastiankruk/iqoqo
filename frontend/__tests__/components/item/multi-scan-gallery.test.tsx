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
import { describe, it, expect, vi, afterEach } from "vitest";
import { MultiScanGallery } from "@/components/item/multi-scan-gallery";
import { useQuery } from "@tanstack/react-query";

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

// Mock Dialog components since we only need to check for presence of Title/Description
vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children }: { children: React.ReactNode }) => <div data-testid="dialog">{children}</div>,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div data-testid="dialog-content">{children}</div>,
  DialogTrigger: ({ children }: { children: React.ReactNode }) => <div data-testid="dialog-trigger">{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2 data-testid="dialog-title">{children}</h2>,
  DialogDescription: ({ children }: { children: React.ReactNode }) => <p data-testid="dialog-description">{children}</p>,
}));

describe("MultiScanGallery Component", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    vi.mocked(useQuery).mockReturnValue({
      isLoading: true,
      data: undefined,
    } as unknown as ReturnType<typeof useQuery>);

    const { container } = render(<MultiScanGallery manifestationId={1} />);
    const loaders = container.querySelectorAll(".animate-pulse");
    expect(loaders.length).toBeGreaterThan(0);
  });

  it("renders empty state", () => {
    vi.mocked(useQuery).mockReturnValue({
      isLoading: false,
      data: [],
    } as unknown as ReturnType<typeof useQuery>);

    render(<MultiScanGallery manifestationId={1} />);
    expect(screen.getByText(/No additional scans/i)).toBeInTheDocument();
  });

  it("renders gallery with images and accessibility tags", () => {
    const mockScans = [
      { id: 1, url: "/static/gallery/front.jpg", label: "front", source: "user", added_at: "2026-04-15" },
      { id: 2, url: "/static/gallery/back.jpg", label: "back", source: "user", added_at: "2026-04-15" },
    ];

    vi.mocked(useQuery).mockReturnValue({
      isLoading: false,
      data: mockScans,
    } as unknown as ReturnType<typeof useQuery>);

    render(<MultiScanGallery manifestationId={1} />);

    // Check if labels appear in the grid (we expect at least one occurrence in the grid and one in the dialog)
    expect(screen.getAllByText("front").length).toBeGreaterThan(0);
    expect(screen.getAllByText("back").length).toBeGreaterThan(0);

    // Check if DialogTitle and DialogDescription exist for accessibility
    const titles = screen.getAllByTestId("dialog-title");
    expect(titles.length).toBeGreaterThan(0);
    expect(titles[0]).toHaveTextContent("front");

    const descriptions = screen.getAllByTestId("dialog-description");
    expect(descriptions.length).toBeGreaterThan(0);
    expect(descriptions[0]).toHaveTextContent(/Viewing front from user/i);
  });
});
