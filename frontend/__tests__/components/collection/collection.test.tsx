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

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { useAddItem, useSetWorkIntent, queryKeys } from "@/lib/api/hooks";
import { AddToCollectionDropdown } from "@/components/collection/add-to-collection-dropdown";
import { apiClient } from "@/lib/api/client";
import React from "react";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe("Collection React Query Key Harmonization", () => {
  let queryClient: QueryClient;
  let invalidateSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
    vi.mocked(useQueryClient).mockReturnValue(queryClient);
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("queryKeys generates matching tuples for shelf invalidations", () => {
    const worksShelfKey = queryKeys.worksShelf();
    expect(worksShelfKey.slice(0, 2)).toEqual(["works", "shelf"]);

    const expressionsShelfKey = queryKeys.expressionsShelf();
    expect(expressionsShelfKey.slice(0, 2)).toEqual(["expressions", "shelf"]);
  });

  it("useAddItem invalidates ['works', 'shelf'] and ['expressions', 'shelf']", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { item_id: 1, manifestation_id: 2 } },
    } as any);

    const { result } = renderHook(() => useAddItem(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ manifestation_id: 2 });
    });

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["works", "shelf"] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["expressions", "shelf"] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["items"] }));
    });
  });

  it("useSetWorkIntent invalidates ['works', 'shelf'] and ['expressions', 'shelf']", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { status: "read" } },
    } as any);

    const { result } = renderHook(() => useSetWorkIntent(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ workId: 42, status: "read" });
    });

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["works", "shelf"] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["expressions", "shelf"] }));
    });
  });

  it("AddToCollectionDropdown invalidates harmonized shelf keys on successful mutation", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { success: true, collections: [] },
    } as any);
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { item_id: 123, manifestation_id: 456 } },
    } as any);

    render(
      <QueryClientProvider client={queryClient}>
        <AddToCollectionDropdown manifestationId={456} />
      </QueryClientProvider>
    );

    fireEvent.click(screen.getByRole("button", { name: /add to collection/i }));
    const libraryBtn = await screen.findByText("Add to My Library");
    fireEvent.click(libraryBtn);

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["works", "shelf"] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["expressions", "shelf"] }));
      expect(invalidateSpy).toHaveBeenCalledWith(expect.objectContaining({ queryKey: ["manifestations"] }));
    });
  });
});
