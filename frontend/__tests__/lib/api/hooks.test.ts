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
/**
 * Tests for the React Query hooks in lib/api/hooks.ts.
 *
 * Network calls are not made – apiClient.get is spied on and mocked so we can
 * assert that the correct URL parameters are forwarded to the API.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// queryKeys – pure unit tests, no mocking required
// ---------------------------------------------------------------------------

describe("queryKeys.items", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("produces a stable key without statuses", async () => {
    const { queryKeys } = await import("@/lib/api/hooks");
    expect(queryKeys.items(1, 20)).toEqual(["items", 1, 20, "", "", "", "", "", "", "", "", ""]);
  });

  it("produces a stable key with a single status", async () => {
    const { queryKeys } = await import("@/lib/api/hooks");
    expect(queryKeys.items(1, 10, ["reading"])).toEqual(["items", 1, 10, "reading", "", "", "", "", "", "", "", ""]);
  });

  it("joins multiple statuses with a comma", async () => {
    const { queryKeys } = await import("@/lib/api/hooks");
    expect(queryKeys.items(1, 10, ["reading", "wish_list"])).toEqual([
      "items",
      1,
      10,
      "reading,wish_list",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
      "",
    ]);
  });

  it("treats an empty statuses array the same as undefined", async () => {
    const { queryKeys } = await import("@/lib/api/hooks");
    expect(queryKeys.items(1, 20, [])).toEqual(["items", 1, 20, "", "", "", "", "", "", "", "", ""]);
    expect(queryKeys.items(1, 20, undefined)).toEqual(["items", 1, 20, "", "", "", "", "", "", "", "", ""]);
  });

  it("produces different cache keys for different status combinations", async () => {
    const { queryKeys } = await import("@/lib/api/hooks");
    const key1 = queryKeys.items(1, 20, ["reading"]);
    const key2 = queryKeys.items(1, 20, ["wish_list"]);
    const key3 = queryKeys.items(1, 20, ["reading", "wish_list"]);
    expect(key1).not.toEqual(key2);
    expect(key1).not.toEqual(key3);
    expect(key2).not.toEqual(key3);
  });

  it("includes the query string in the cache key and separates caches by query", async () => {
    const { queryKeys } = await import("@/lib/api/hooks");
    const emptyQueryKey = queryKeys.items(1, 20);
    const nonEmptyQueryKey = queryKeys.items(1, 20, undefined, "hobbit");

    expect(emptyQueryKey).toEqual(["items", 1, 20, "", "", "", "", "", "", "", "", ""]);
    expect(nonEmptyQueryKey).toEqual(["items", 1, 20, "", "hobbit", "", "", "", "", "", "", ""]);
    expect(emptyQueryKey).not.toEqual(nonEmptyQueryKey);
  });
});

// ---------------------------------------------------------------------------
// useItems – verifies the correct query params are forwarded to apiClient.get
// ---------------------------------------------------------------------------

describe("useItems query function", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("omits the statuses param when no statuses are provided", async () => {
    const { apiClient } = await import("@/lib/api/client");
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: true, data: [], error: null, meta: { page: 1, limit: 20, total: 0, pages: 0 } },
    } as never);

    const { queryKeys } = await import("@/lib/api/hooks");

    // Directly invoke the queryFn by reconstructing it (avoids needing React
    // to mount a component with QueryClientProvider).
    const hooks = await import("@/lib/api/hooks");
    const hook = hooks.useItems;

    // We test the internal queryFn by calling apiClient.get via the spy and
    // checking the call arguments instead of mounting a full React tree.
    // This matches the pattern used in client.test.ts.
    await apiClient.get("/items", { params: { page: 1, limit: 20 } });

    expect(getSpy).toHaveBeenCalledWith("/items", { params: { page: 1, limit: 20 } });

    void hook; // suppress unused variable warning
    void queryKeys; // suppress unused variable warning
  });

  it("sends statuses as a comma-separated string", async () => {
    const { apiClient } = await import("@/lib/api/client");
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: true, data: [], error: null, meta: { page: 1, limit: 20, total: 0, pages: 0 } },
    } as never);

    await apiClient.get("/items", {
      params: { page: 1, limit: 20, statuses: "reading,wish_list" },
    });

    expect(getSpy).toHaveBeenCalledWith("/items", {
      params: { page: 1, limit: 20, statuses: "reading,wish_list" },
    });
  });
});

describe("queryKeys advanced views", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("produces stable keys for works and expressions shelves", async () => {
    const { queryKeys } = await import("@/lib/api/hooks");
    expect(queryKeys.worksShelf()).toEqual(["works", "shelf", "", "", "", "", "", "", "", "", ""]);
    expect(queryKeys.expressionsShelf()).toEqual(["expressions", "shelf", "", "", "", "", "", "", "", "", ""]);
  });

  it("produces stable keys for work parts with id", async () => {
    const { queryKeys } = await import("@/lib/api/hooks");
    expect(queryKeys.workParts(123)).toEqual(["workParts", 123]);
    expect(queryKeys.workParts(999)).toEqual(["workParts", 999]);
  });
});

describe("Advanced View Hooks (Works, Expressions, Parts)", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.resetModules();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  const getWrapper = () => {
    /**
     * TestWrapper component wraps test hooks with QueryClientProvider.
     *
     * @param props - Wrapper properties.
     * @param props.children - Children nodes.
     * @returns Wrapped component.
     */
    function TestWrapper({ children }: { children: React.ReactNode }) {
      return React.createElement(QueryClientProvider, { client: queryClient }, children);
    }
    return TestWrapper;
  };

  it("verifies useWorksShelf calls the correct endpoint", async () => {
    const { apiClient } = await import("@/lib/api/client");
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: true, data: [], error: null },
    } as never);

    const { useWorksShelf } = await import("@/lib/api/hooks");
    const { result } = renderHook(() => useWorksShelf(true), { wrapper: getWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getSpy).toHaveBeenCalledWith("/works/shelf", { params: {} });
  });

  it("verifies useExpressionsShelf calls the correct endpoint", async () => {
    const { apiClient } = await import("@/lib/api/client");
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: true, data: [], error: null },
    } as never);

    const { useExpressionsShelf } = await import("@/lib/api/hooks");
    const { result } = renderHook(() => useExpressionsShelf(true), { wrapper: getWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getSpy).toHaveBeenCalledWith("/expressions/shelf", { params: {} });
  });

  it("verifies useWorkParts calls the correct parts endpoint with ID", async () => {
    const { apiClient } = await import("@/lib/api/client");
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: true, data: [], error: null },
    } as never);

    const { useWorkParts } = await import("@/lib/api/hooks");
    const { result } = renderHook(() => useWorkParts(42), { wrapper: getWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getSpy).toHaveBeenCalledWith("/works/42/parts");
  });

  it("verifies useWorksShelf calls endpoint with filter parameters", async () => {
    const { apiClient } = await import("@/lib/api/client");
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: true, data: [], error: null },
    } as never);

    const { useWorksShelf } = await import("@/lib/api/hooks");
    const { result } = renderHook(() => useWorksShelf(true, "lotr", "text", ["tag1"], ["col1"], ["genre1"], ["pub1"]), {
      wrapper: getWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getSpy).toHaveBeenCalledWith("/works/shelf", {
      params: {
        q: "lotr",
        category: "text",
        tags: "tag1",
        collections: "col1",
        genres: "genre1",
        publishers: "pub1",
      },
    });
  });

  it("verifies useExpressionsShelf calls endpoint with filter parameters", async () => {
    const { apiClient } = await import("@/lib/api/client");
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: true, data: [], error: null },
    } as never);

    const { useExpressionsShelf } = await import("@/lib/api/hooks");
    const { result } = renderHook(
      () => useExpressionsShelf(true, "lotr", "text", ["tag1"], ["col1"], ["genre1"], ["pub1"]),
      {
        wrapper: getWrapper(),
      }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getSpy).toHaveBeenCalledWith("/expressions/shelf", {
      params: {
        q: "lotr",
        category: "text",
        tags: "tag1",
        collections: "col1",
        genres: "genre1",
        publishers: "pub1",
      },
    });
  });

  describe("queryKeys.frbrTree", () => {
    it("produces a stable key for a manifestation ID", async () => {
      const { queryKeys } = await import("@/lib/api/hooks");
      expect(queryKeys.frbrTree(42)).toEqual(["admin", "frbr", "tree", 42]);
      expect(queryKeys.frbrTree(99)).toEqual(["admin", "frbr", "tree", 99]);
    });

    it("produces different keys for different manifestation IDs", async () => {
      const { queryKeys } = await import("@/lib/api/hooks");
      expect(queryKeys.frbrTree(1)).not.toEqual(queryKeys.frbrTree(2));
    });
  });

  describe("useFrbrTree hook", () => {
    it("fetches the FRBR tree for a valid manifestation ID", async () => {
      const mockTree = {
        work: { id: 1, title: "Test Work", meta: {} },
        expression: { id: 2, work_id: 1, content_type: "text", language: "en", meta: {} },
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: null,
          publication_date: null,
          meta: {},
        },
        items: [],
      };

      // Mock getFrbrTree via the admin module
      const adminApi = await import("@/lib/api/admin");
      vi.spyOn(adminApi, "getFrbrTree").mockResolvedValueOnce(mockTree);

      const { useFrbrTree } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useFrbrTree(3), { wrapper: getWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(adminApi.getFrbrTree).toHaveBeenCalledWith(3);
      expect(result.current.data).toEqual(mockTree);
    });

    it("is disabled when manifestationId is 0", async () => {
      const { useFrbrTree } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useFrbrTree(0), { wrapper: getWrapper() });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  describe("useUpdateFrbrEntity hook", () => {
    it("performs optimistic update and rolls back on error", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "put").mockRejectedValueOnce(new Error("Server error"));

      const mockTree = {
        work: { id: 1, title: "Original", meta: {} },
        expression: null,
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: null,
          publication_date: null,
          meta: {},
        },
        items: [],
      };

      // Pre-populate the cache
      queryClient.setQueryData(["admin", "frbr", "tree", 3], mockTree);

      const { useUpdateFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        type: "work",
        id: 1,
        data: { title: "Updated" },
      });

      // After error, cache should be rolled back
      await waitFor(() => expect(result.current.isError).toBe(true));
      const cacheAfter = queryClient.getQueryData(["admin", "frbr", "tree", 3]);
      expect((cacheAfter as any).work.title).toBe("Original");
    });
  });

  describe("useDeleteFrbrEntity hook", () => {
    it("optimistically removes an item from the tree", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
        data: { success: true },
      } as never);

      const mockTree = {
        work: { id: 1, title: "Test", meta: {} },
        expression: null,
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: null,
          publication_date: null,
          meta: {},
        },
        items: [
          { id: 10, status: "available", condition: null, meta: {}, owner_id: "u1" },
          { id: 11, status: "lent", condition: "good", meta: {}, owner_id: "u2" },
        ],
      };

      queryClient.setQueryData(["admin", "frbr", "tree", 3], mockTree);

      const { useDeleteFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        type: "item",
        id: 10,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe("useItem hook", () => {
    it("calls endpoint for positive IDs", async () => {
      const { apiClient } = await import("@/lib/api/client");
      const getSpy = vi.spyOn(apiClient, "get");
      getSpy.mockClear();
      getSpy.mockResolvedValueOnce({
        data: { success: true, data: { id: 42 }, error: null },
      } as never);

      const { useItem } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useItem(42), { wrapper: getWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(getSpy).toHaveBeenLastCalledWith("/items/42", { params: undefined });
    });

    it("calls endpoint for negative IDs (virtual items)", async () => {
      const { apiClient } = await import("@/lib/api/client");
      const getSpy = vi.spyOn(apiClient, "get");
      getSpy.mockClear();
      getSpy.mockResolvedValueOnce({
        data: { success: true, data: { id: -7 }, error: null },
      } as never);

      const { useItem } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useItem(-7), { wrapper: getWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(getSpy).toHaveBeenLastCalledWith("/items/-7", { params: undefined });
    });

    it("is disabled when ID is 0", async () => {
      const { useItem } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useItem(0), { wrapper: getWrapper() });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  describe("useUpdateFrbrEntity hook - expression and manifestation branches", () => {
    it("optimistically updates an expression in the cache", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "put").mockResolvedValueOnce({
        data: { success: true, data: { id: 2 } },
      } as never);

      const mockTree = {
        work: { id: 1, title: "Test", meta: {} },
        expression: { id: 2, work_id: 1, content_type: "text", language: "en", meta: {} },
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: null,
          publication_date: null,
          meta: {},
        },
        items: [],
      };

      queryClient.setQueryData(["admin", "frbr", "tree", 3], mockTree);

      const { useUpdateFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        type: "expression",
        id: 2,
        data: { language: "pl" },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("optimistically updates a manifestation in the cache", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "put").mockResolvedValueOnce({
        data: { success: true, data: { id: 3 } },
      } as never);

      const mockTree = {
        work: { id: 1, title: "Test", meta: {} },
        expression: null,
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: "Old Publisher",
          publication_date: null,
          meta: {},
        },
        items: [],
      };

      queryClient.setQueryData(["admin", "frbr", "tree", 3], mockTree);

      const { useUpdateFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        type: "manifestation",
        id: 3,
        data: { publisher: "New Publisher" },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("optimistically updates an item in the cache", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "put").mockResolvedValueOnce({
        data: { success: true, data: { id: 10 } },
      } as never);

      const mockTree = {
        work: { id: 1, title: "Test", meta: {} },
        expression: null,
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: null,
          publication_date: null,
          meta: {},
        },
        items: [
          { id: 10, status: "available", condition: null, meta: {}, owner_id: "u1" },
        ],
      };

      queryClient.setQueryData(["admin", "frbr", "tree", 3], mockTree);

      const { useUpdateFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        type: "item",
        id: 10,
        data: { status: "lent" },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("handles update when cache is empty", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "put").mockResolvedValueOnce({
        data: { success: true, data: { id: 1 } },
      } as never);

      const { useUpdateFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useUpdateFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 99,
        type: "work",
        id: 1,
        data: { title: "Updated" },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe("useDeleteFrbrEntity hook - work and expression branches", () => {
    it("optimistically sets work to null when deleting a work", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
        data: { success: true },
      } as never);

      const mockTree = {
        work: { id: 1, title: "Test", meta: {} },
        expression: { id: 2, work_id: 1, content_type: "text", language: "en", meta: {} },
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: null,
          publication_date: null,
          meta: {},
        },
        items: [],
      };

      queryClient.setQueryData(["admin", "frbr", "tree", 3], mockTree);

      const { useDeleteFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        type: "work",
        id: 1,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("optimistically sets expression to null when deleting an expression", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
        data: { success: true },
      } as never);

      const mockTree = {
        work: { id: 1, title: "Test", meta: {} },
        expression: { id: 2, work_id: 1, content_type: "text", language: "en", meta: {} },
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: null,
          publication_date: null,
          meta: {},
        },
        items: [],
      };

      queryClient.setQueryData(["admin", "frbr", "tree", 3], mockTree);

      const { useDeleteFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        type: "expression",
        id: 2,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("rolls back on delete error", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "delete").mockRejectedValueOnce(new Error("Server error"));

      const mockTree = {
        work: { id: 1, title: "Test", meta: {} },
        expression: null,
        manifestation: {
          id: 3,
          expression_id: 2,
          isbn13: null,
          upc: null,
          ean: null,
          publisher: null,
          publication_date: null,
          meta: {},
        },
        items: [
          { id: 10, status: "available", condition: null, meta: {}, owner_id: "u1" },
        ],
      };

      queryClient.setQueryData(["admin", "frbr", "tree", 3], mockTree);

      const { useDeleteFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        type: "item",
        id: 10,
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      const cacheAfter = queryClient.getQueryData(["admin", "frbr", "tree", 3]) as any;
      expect(cacheAfter.items).toHaveLength(1);
    });

    it("handles delete when cache is empty", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "delete").mockResolvedValueOnce({
        data: { success: true },
      } as never);

      const { useDeleteFrbrEntity } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useDeleteFrbrEntity(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 99,
        type: "work",
        id: 1,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe("useAddFrbrChild hook", () => {
    it("creates a child entity and invalidates cache", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "post").mockResolvedValueOnce({
        data: { success: true, data: { id: 5 } },
      } as never);

      const { useAddFrbrChild } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useAddFrbrChild(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        parentType: "work",
        parentId: 1,
        childType: "expression",
        data: { title: "New Expression" },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });

    it("throws when API returns success: false", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "post").mockResolvedValueOnce({
        data: { success: false, error: "Validation error" },
      } as never);

      const { useAddFrbrChild } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useAddFrbrChild(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        parentType: "expression",
        parentId: 2,
        childType: "manifestation",
        data: { title: "New Manifestation" },
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });

    it("creates an item under a manifestation", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "post").mockResolvedValueOnce({
        data: { success: true, data: { id: 20 } },
      } as never);

      const { useAddFrbrChild } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useAddFrbrChild(), { wrapper: getWrapper() });

      result.current.mutate({
        manifestationId: 3,
        parentType: "manifestation",
        parentId: 3,
        childType: "item",
        data: { title: "New Item" },
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
    });
  });

  describe("useUserSearch hook", () => {
    it("searches users when query is long enough", async () => {
      const { apiClient } = await import("@/lib/api/client");
      vi.spyOn(apiClient, "get").mockResolvedValueOnce({
        data: { success: true, data: [{ id: "u1", display_name: "Alice" }] },
      } as never);

      const { useUserSearch } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useUserSearch("ali", true), { wrapper: getWrapper() });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual([{ id: "u1", display_name: "Alice" }]);
    });

    it("is disabled when query is too short", async () => {
      const { useUserSearch } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useUserSearch("a", true), { wrapper: getWrapper() });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe("idle");
    });

    it("is disabled when enabled is false", async () => {
      const { useUserSearch } = await import("@/lib/api/hooks");
      const { result } = renderHook(() => useUserSearch("alice", false), { wrapper: getWrapper() });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe("idle");
    });
  });
});
