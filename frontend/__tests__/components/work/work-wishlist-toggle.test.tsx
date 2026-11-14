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

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { WorkDetailClient } from "@/components/work/work-detail-client";
import type { WorkDetail } from "@/types/frbr";
import { toast } from "sonner";

const mockCreateMutateAsync = vi.fn();
const mockDeleteMutateAsync = vi.fn();
const mockUseWishlist = vi.fn();
const mockUseProfile = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/work/100"),
  useParams: () => ({ id: "100" }),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

vi.mock("@/lib/api/hooks", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks")>();
  return {
    ...actual,
    useWork: (_id: number, initial?: WorkDetail | null) => ({ data: initial, isLoading: false }),
    useProfile: () => mockUseProfile(),
  };
});

vi.mock("@/lib/api/wishlist", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/wishlist")>();
  return {
    ...actual,
    useWishlist: (params?: Record<string, unknown>, enabled?: boolean) => mockUseWishlist(params, enabled),
    useCreateWishlistItem: () => ({ mutateAsync: mockCreateMutateAsync, isPending: false }),
    useDeleteWishlistItem: () => ({ mutateAsync: mockDeleteMutateAsync, isPending: false }),
  };
});

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const sampleWork: WorkDetail = {
  id: 100,
  title: "Foundation",
  authors: ["Isaac Asimov"],
  meta: { authors: ["Isaac Asimov"] },
  expressions: [],
};

/** Render component wrapped in QueryClientProvider. */
function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("WorkDetailClient wishlist toggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("hides wishlist button when user is unauthenticated", () => {
    mockUseProfile.mockReturnValue({ data: undefined });
    mockUseWishlist.mockReturnValue({ data: undefined });

    renderWithQuery(<WorkDetailClient workId={100} initialWork={sampleWork} />);

    expect(screen.queryByRole("button", { name: /add to wishlist|on wishlist/i })).not.toBeInTheDocument();
  });

  it("creates a work-level wishlist entry when clicked for authenticated user", async () => {
    mockUseProfile.mockReturnValue({ data: { id: 1, email: "reader@iqoqo.local" } });
    mockUseWishlist.mockReturnValue({ data: { data: [], total: 0 } });
    mockCreateMutateAsync.mockResolvedValueOnce({ id: 55, work_id: 100 });

    renderWithQuery(<WorkDetailClient workId={100} initialWork={sampleWork} />);

    const addBtn = screen.getByRole("button", { name: /add to wishlist/i });
    fireEvent.click(addBtn);

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalledWith({ work_id: 100 });
      expect(toast.success).toHaveBeenCalledWith("Added to wishlist");
    });
  });

  it("removes existing work-level wishlist entry when already on wishlist", async () => {
    mockUseProfile.mockReturnValue({ data: { id: 1, email: "reader@iqoqo.local" } });
    mockUseWishlist.mockReturnValue({
      data: { data: [{ id: 55, work_id: 100 }], total: 1 },
    });
    mockDeleteMutateAsync.mockResolvedValueOnce(undefined);

    renderWithQuery(<WorkDetailClient workId={100} initialWork={sampleWork} />);

    const removeBtn = screen.getByRole("button", { name: /on wishlist/i });
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith(55);
      expect(toast.success).toHaveBeenCalledWith("Removed from wishlist");
    });
  });
});
