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
  useQuery: vi.fn(() => ({ data: [], isLoading: false })),
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

vi.mock("@/lib/api/escalations", () => ({
  useCreateEscalation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useMyEscalations: vi.fn(() => ({ data: [], isLoading: false })),
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

  it("configures declarative useQuery refetchInterval for 3s polling when cover is pending or processing", async () => {
    const { useQuery } = await import("@tanstack/react-query");
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    const pendingManifestation = {
      ...mockManifestation,
      meta: { cover_status: "pending" },
    } as unknown as Manifestation;
    render(<ManifestationActions manifestation={pendingManifestation} />);

    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ["manifestation", pendingManifestation.id],
        enabled: true,
        refetchInterval: expect.any(Function),
      })
    );

    const call = vi
      .mocked(useQuery)
      .mock.calls.find(
        c => JSON.stringify(c[0]?.queryKey) === JSON.stringify(["manifestation", pendingManifestation.id])
      );
    const refetchInterval = call?.[0]?.refetchInterval as (query: any) => number | false;
    expect(refetchInterval({ state: { data: { meta: { cover_status: "pending" } } } })).toBe(3000);
    expect(refetchInterval({ state: { data: { meta: { cover_status: "processing" } } } })).toBe(3000);
    expect(refetchInterval({ state: { data: { meta: { cover_status: "ready" } } } })).toBe(false);
  });

  it("disables declarative polling when cover_status is ready", async () => {
    const { useQuery } = await import("@tanstack/react-query");
    vi.mocked(hooks.useProfile).mockReturnValue({
      data: { id: "test-id", email: "test@example.com", permissions: [] },
    } as unknown as ReturnType<typeof hooks.useProfile>);

    render(<ManifestationActions manifestation={mockManifestation} />);

    expect(useQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ["manifestation", mockManifestation.id],
        enabled: false,
      })
    );
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

  describe("Edit FRBR button visibility (write:metadata)", () => {
    it("does NOT render Edit FRBR for user with read:metadata but WITHOUT write:metadata", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "test-id",
          email: "test@example.com",
          permissions: ["read:metadata"],
        },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      render(<ManifestationActions manifestation={mockManifestation} />);

      expect(screen.queryByText(/Admin Actions/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Edit FRBR/i)).not.toBeInTheDocument();
    });

    it("renders Edit FRBR for user with write:metadata permission", () => {
      vi.mocked(hooks.useProfile).mockReturnValue({
        data: {
          id: "test-id",
          email: "test@example.com",
          permissions: ["write:metadata"],
        },
      } as unknown as ReturnType<typeof hooks.useProfile>);

      render(<ManifestationActions manifestation={mockManifestation} />);

      fireEvent.click(screen.getByText(/Admin Actions/i));
      expect(screen.getByText(/Edit FRBR/i)).toBeInTheDocument();
    });
  });
});
