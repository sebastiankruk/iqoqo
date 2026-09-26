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
import { renderHook, waitFor } from "@testing-library/react";
import { useQueryClient } from "@tanstack/react-query";
import { useFrbrTree, useUpdateFrbrEntity, useAddFrbrChild, useDeleteFrbrEntity } from "@/lib/api/hooks/admin";
import { apiClient, apiFetch } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/hooks/query-keys";
import type { FrbrTree } from "@/lib/api/admin";
import { createTestQueryClient, createTestQueryWrapper } from "./test-utils";

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
  apiClient: {
    put: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    get: vi.fn(),
  },
}));

const mockTree: FrbrTree = {
  work: {
    id: 1,
    title: "Dune",
    meta: { original_language: "en" },
  },
  expression: {
    id: 2,
    work_id: 1,
    content_type: "text",
    language: "en",
    kind: "novel",
    meta: {},
  },
  manifestation: {
    id: 3,
    expression_id: 2,
    isbn13: "9780441172719",
    upc: null,
    ean: null,
    publisher: "Ace Books",
    publication_date: "1965-08-01",
    meta: { type: "Book", pages: "412" },
  },
  items: [
    {
      id: 10,
      condition: "like_new",
      status: "available",
      meta: {},
      owner_id: "user1",
      owner_name: "Test User",
    },
    {
      id: 11,
      condition: "good",
      status: "lent",
      meta: {},
      owner_id: "user2",
      owner_name: "Other User",
    },
  ],
};

describe("FRBR TanStack Query Hooks", () => {
  let queryClient = createTestQueryClient();
  let wrapper = createTestQueryWrapper(queryClient);

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = createTestQueryClient();
    wrapper = createTestQueryWrapper(queryClient);
    vi.mocked(useQueryClient).mockReturnValue(queryClient);
  });

  // -------------------------------------------------------------------------
  // useFrbrTree
  // -------------------------------------------------------------------------

  it("useFrbrTree fetches tree data when manifestationId > 0", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(mockTree);

    const { result } = renderHook(() => useFrbrTree(3), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiFetch).toHaveBeenCalledWith("/v1/admin/frbr/tree/manifestation/3");
    expect(result.current.data).toEqual(mockTree);
  });

  it("useFrbrTree disabled guard: does not initiate fetch when manifestationId <= 0", () => {
    const { result } = renderHook(() => useFrbrTree(0), { wrapper });

    expect(result.current.fetchStatus).toBe("idle");
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("useFrbrTree error propagation: propagates error state when fetch fails", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("Network timeout"));

    const { result } = renderHook(() => useFrbrTree(3), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe("Network timeout");
  });

  // -------------------------------------------------------------------------
  // useUpdateFrbrEntity
  // -------------------------------------------------------------------------

  it("useUpdateFrbrEntity optimistic update for Work patches tree.work in cache", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    let resolveApi: (value: unknown) => void;
    vi.mocked(apiClient.put).mockReturnValue(
      new Promise(resolve => {
        resolveApi = resolve;
      })
    );

    const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper });

    const mutatePromise = result.current.mutateAsync({
      manifestationId: 3,
      type: "work",
      id: 1,
      data: { title: "Dune Messiah", meta: { original_language: "en" } },
    });

    await waitFor(() => {
      const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
      expect(cached?.work?.title).toBe("Dune Messiah");
    });

    resolveApi!({ data: { success: true, data: { id: 1 } } });
    await mutatePromise;
  });

  it("useUpdateFrbrEntity optimistic update for Expression patches target expression in cache", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    let resolveApi: (value: unknown) => void;
    vi.mocked(apiClient.put).mockReturnValue(
      new Promise(resolve => {
        resolveApi = resolve;
      })
    );

    const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper });

    const mutatePromise = result.current.mutateAsync({
      manifestationId: 3,
      type: "expression",
      id: 2,
      data: { content_type: "audio", language: "pl" },
    });

    await waitFor(() => {
      const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
      expect(cached?.expression?.content_type).toBe("audio");
      expect(cached?.expression?.language).toBe("pl");
    });

    resolveApi!({ data: { success: true, data: { id: 2 } } });
    await mutatePromise;
  });

  it("useUpdateFrbrEntity optimistic update for Manifestation patches target manifestation in cache", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    let resolveApi: (value: unknown) => void;
    vi.mocked(apiClient.put).mockReturnValue(
      new Promise(resolve => {
        resolveApi = resolve;
      })
    );

    const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper });

    const mutatePromise = result.current.mutateAsync({
      manifestationId: 3,
      type: "manifestation",
      id: 3,
      data: { publisher: "Tor Books" },
    });

    await waitFor(() => {
      const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
      expect(cached?.manifestation.publisher).toBe("Tor Books");
    });

    resolveApi!({ data: { success: true, data: { id: 3 } } });
    await mutatePromise;
  });

  it("useUpdateFrbrEntity optimistic update for Item patches target item in tree.items", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    let resolveApi: (value: unknown) => void;
    vi.mocked(apiClient.put).mockReturnValue(
      new Promise(resolve => {
        resolveApi = resolve;
      })
    );

    const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper });

    const mutatePromise = result.current.mutateAsync({
      manifestationId: 3,
      type: "item",
      id: 10,
      data: { status: "lent", condition: "fair" },
    });

    await waitFor(() => {
      const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
      const item = cached?.items.find(i => i.id === 10);
      expect(item?.status).toBe("lent");
      expect(item?.condition).toBe("fair");
    });

    resolveApi!({ data: { success: true, data: { id: 10 } } });
    await mutatePromise;
  });

  it("useUpdateFrbrEntity rollback on error reverts cache to pre-mutation snapshot", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    vi.mocked(apiClient.put).mockRejectedValueOnce(new Error("Update failed"));

    const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper });

    await expect(
      result.current.mutateAsync({
        manifestationId: 3,
        type: "work",
        id: 1,
        data: { title: "Invalid Title" },
      })
    ).rejects.toThrow("Update failed");

    const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
    expect(cached?.work?.title).toBe("Dune");
  });

  it("useUpdateFrbrEntity cache invalidation on settled invalidates frbrTree query", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    vi.mocked(apiClient.put).mockResolvedValueOnce({
      data: { success: true, data: { id: 1 } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper });

    await result.current.mutateAsync({
      manifestationId: 3,
      type: "work",
      id: 1,
      data: { title: "Dune Messiah" },
    });

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: queryKeys.frbrTree(3),
    });
  });

  // -------------------------------------------------------------------------
  // useAddFrbrChild
  // -------------------------------------------------------------------------

  it("useAddFrbrChild successful creation invalidates frbrTree query", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, data: { id: 50 } },
    });
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useAddFrbrChild(), { wrapper });

    const created = await result.current.mutateAsync({
      manifestationId: 3,
      parentType: "work",
      parentId: 1,
      childType: "expression",
      data: { title: "Audiobook" },
    });

    expect(created).toEqual({ id: 50 });
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: queryKeys.frbrTree(3),
    });
  });

  it("useAddFrbrChild API failure throws error when success is false", async () => {
    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: false, error: "Validation failed" },
    });

    const { result } = renderHook(() => useAddFrbrChild(), { wrapper });

    await expect(
      result.current.mutateAsync({
        manifestationId: 3,
        parentType: "work",
        parentId: 1,
        childType: "expression",
        data: { title: "Invalid" },
      })
    ).rejects.toThrow("Validation failed");
  });

  // -------------------------------------------------------------------------
  // useDeleteFrbrEntity
  // -------------------------------------------------------------------------

  it("useDeleteFrbrEntity optimistic removal of Work sets tree.work to null", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    let resolveApi: (value: unknown) => void;
    vi.mocked(apiClient.delete).mockReturnValue(
      new Promise(resolve => {
        resolveApi = resolve;
      })
    );

    const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper });

    const mutatePromise = result.current.mutateAsync({
      manifestationId: 3,
      type: "work",
      id: 1,
    });

    await waitFor(() => {
      const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
      expect(cached?.work).toBeNull();
    });

    resolveApi!({});
    await mutatePromise;
  });

  it("useDeleteFrbrEntity optimistic removal of Item filters item from tree.items", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    let resolveApi: (value: unknown) => void;
    vi.mocked(apiClient.delete).mockReturnValue(
      new Promise(resolve => {
        resolveApi = resolve;
      })
    );

    const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper });

    const mutatePromise = result.current.mutateAsync({
      manifestationId: 3,
      type: "item",
      id: 10,
    });

    await waitFor(() => {
      const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
      expect(cached?.items.some(i => i.id === 10)).toBe(false);
      expect(cached?.items.some(i => i.id === 11)).toBe(true);
    });

    resolveApi!({});
    await mutatePromise;
  });

  it("useDeleteFrbrEntity optimistic removal of Expression sets tree.expression to null", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    let resolveApi: (value: unknown) => void;
    vi.mocked(apiClient.delete).mockReturnValue(
      new Promise(resolve => {
        resolveApi = resolve;
      })
    );

    const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper });

    const mutatePromise = result.current.mutateAsync({
      manifestationId: 3,
      type: "expression",
      id: 2,
    });

    await waitFor(() => {
      const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
      expect(cached?.expression).toBeNull();
    });

    resolveApi!({});
    await mutatePromise;
  });

  it("useUpdateFrbrEntity normalizes array metadata fields", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    vi.mocked(apiClient.put).mockResolvedValueOnce({
      data: { success: true, data: { id: 1 } },
    });

    const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper });

    await result.current.mutateAsync({
      manifestationId: 3,
      type: "work",
      id: 1,
      data: {
        title: "Dune",
        meta: {
          genres: "sci-fi",
        },
      },
    });

    expect(apiClient.put).toHaveBeenCalledWith(
      "/v1/admin/frbr/work/1",
      expect.objectContaining({
        meta: expect.objectContaining({
          genres: ["sci-fi"],
        }),
      })
    );
  });

  it("useUpdateFrbrEntity and useDeleteFrbrEntity gracefully handle missing cache", async () => {
    vi.mocked(apiClient.put).mockResolvedValueOnce({
      data: { success: true, data: { id: 1 } },
    });
    vi.mocked(apiClient.delete).mockResolvedValueOnce({});

    const { result: updateResult } = renderHook(() => useUpdateFrbrEntity(), { wrapper });
    await updateResult.current.mutateAsync({
      manifestationId: 3,
      type: "work",
      id: 1,
      data: { title: "Dune" },
    });
    expect(queryClient.getQueryData(queryKeys.frbrTree(3))).toBeUndefined();

    const { result: deleteResult } = renderHook(() => useDeleteFrbrEntity(), { wrapper });
    await deleteResult.current.mutateAsync({
      manifestationId: 3,
      type: "work",
      id: 1,
    });
    expect(queryClient.getQueryData(queryKeys.frbrTree(3))).toBeUndefined();
  });

  it("useDeleteFrbrEntity rollback on error reverts cache to snapshot", async () => {
    queryClient.setQueryData(queryKeys.frbrTree(3), mockTree);
    vi.mocked(apiClient.delete).mockRejectedValueOnce(new Error("Cannot delete item"));

    const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper });

    await expect(
      result.current.mutateAsync({
        manifestationId: 3,
        type: "item",
        id: 10,
      })
    ).rejects.toThrow("Cannot delete item");

    const cached = queryClient.getQueryData<FrbrTree>(queryKeys.frbrTree(3));
    expect(cached?.items.some(i => i.id === 10)).toBe(true);
  });
});
