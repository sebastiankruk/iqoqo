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
import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { ManifestationActions } from "@/components/manifestation/manifestation-actions";
import * as hooks from "@/lib/api/hooks";
import type { Manifestation } from "@/types/frbr";

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
  useRegenerateCover: vi.fn(() => ({ mutateAsync: vi.fn() })),
  queryKeys: { manifestation: vi.fn((id: number) => ["manifestation", id]) },
}));

const mockInvalidateQueries = vi.fn();

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: vi.fn(() => ({ setQueryData: vi.fn(), invalidateQueries: mockInvalidateQueries })),
}));

// Mock CameraCapture since it's a subcomponent
vi.mock("@/components/scanner/camera-capture", () => ({
  CameraCapture: () => <div data-testid="camera-capture">CameraCapture</div>,
}));

const mockManifestation = {
  id: 1,
  expression_id: 1,
  cover_url: "/static/covers/123.jpg",
  meta: {
    cover_status: "ready",
  },
} as unknown as Manifestation;

describe("ManifestationActions Component", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("renders no buttons if user has no permissions", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    render(<ManifestationActions manifestation={mockManifestation} />);

    expect(screen.queryByText(/Refetch Metadata/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Regenerate Cover/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId("camera-capture")).not.toBeInTheDocument();
    expect(screen.queryByText(/Delete manifestation/i)).not.toBeInTheDocument();
  });

  it("starts polling invalidateQueries every 3s when cover_status is pending", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    const pendingManifestation = {
      ...mockManifestation,
      meta: { cover_status: "pending" },
    } as unknown as Manifestation;
    render(<ManifestationActions manifestation={pendingManifestation} />);

    expect(mockInvalidateQueries).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(1);
    expect(mockInvalidateQueries).toHaveBeenCalledWith({
      queryKey: ["manifestation", pendingManifestation.id],
    });

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(2);
  });

  it("stops polling when cover_status changes from pending to ready", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    const pendingManifestation = {
      ...mockManifestation,
      meta: { cover_status: "pending" },
    } as unknown as Manifestation;
    const { rerender } = render(<ManifestationActions manifestation={pendingManifestation} />);

    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(1);

    // Cover becomes ready
    rerender(<ManifestationActions manifestation={mockManifestation} />);

    act(() => {
      vi.advanceTimersByTime(6000);
    });
    // Should remain at 1 call since polling stopped
    expect(mockInvalidateQueries).toHaveBeenCalledTimes(1);
  });

  it("renders permitted buttons inside Admin Actions panel when expanded", () => {
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: {
        id: "test-id",
        email: "test@example.com",
        permissions: ["refetch:metadata", "regenerate:cover", "upload:cover", "delete:manifestation"],
      },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    render(<ManifestationActions manifestation={mockManifestation} />);

    // Collapsed by default
    expect(screen.queryByText(/Refetch Metadata/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Regenerate Cover/i)).not.toBeInTheDocument();

    // Click Admin Actions to expand
    fireEvent.click(screen.getByText(/Admin Actions/i));

    expect(screen.getByText(/Refetch Metadata/i)).toBeInTheDocument();
    expect(screen.getByText(/Regenerate Cover/i)).toBeInTheDocument();
    expect(screen.getByTestId("camera-capture")).toBeInTheDocument();
    expect(screen.getByText(/Delete manifestation/i)).toBeInTheDocument();
  });
});
