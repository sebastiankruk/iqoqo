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
 * Tests for the infinite query hooks (useInfiniteItems, useInfiniteManifestations).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useInfiniteItems, useInfiniteManifestations } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

/**
 * Wrapper component providing a QueryClient to the tested hooks.
 *
 * @param root0 - Component props
 * @param root0.children - Child components
 * @returns {JSX.Element} The wrapped component tree
 */
function Wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useInfiniteItems", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it("fetches the first page and computes hasNextPage=true when more pages exist", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        data: [{ id: 1, title: "Item 1" }],
        meta: { page: 1, pages: 2, total: 2 },
      },
    });

    const { result } = renderHook(() => useInfiniteItems(20), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith("/items", {
      params: expect.objectContaining({ page: 1, limit: 20 }),
    });
    expect(result.current.hasNextPage).toBe(true);
  });

  it("computes hasNextPage=false when on the last page", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        data: [{ id: 2, title: "Item 2" }],
        meta: { page: 2, pages: 2, total: 2 },
      },
    });

    const { result } = renderHook(() => useInfiniteItems(20), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.hasNextPage).toBe(false);
  });

  it("forwards filter params to the API", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        data: [],
        meta: { page: 1, pages: 1, total: 0 },
      },
    });

    renderHook(
      () =>
        useInfiniteItems(
          10,
          ["reading"],
          "dune",
          "title",
          true,
          "fiction",
          "book",
          false,
          true,
          false
        ),
      { wrapper: Wrapper }
    );

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith("/items", {
        params: expect.objectContaining({
          page: 1,
          limit: 10,
          statuses: "reading",
          q: "dune",
          sort: "title",
          category: "fiction",
          format: "book",
          missing_cover: true,
        }),
      });
    });
  });
});

describe("useInfiniteManifestations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it("fetches the first page and computes hasNextPage=true when more pages exist", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        data: [{ manifestation_id: 1, title: "Manifestation 1" }],
        meta: { page: 1, pages: 3, total: 5 },
      },
    });

    const { result } = renderHook(() => useInfiniteManifestations(20), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClient.get).toHaveBeenCalledWith("/manifestations", {
      params: expect.objectContaining({ page: 1, limit: 20 }),
    });
    expect(result.current.hasNextPage).toBe(true);
  });

  it("computes hasNextPage=false when on the last page", async () => {
    (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      data: {
        data: [{ manifestation_id: 3, title: "Last" }],
        meta: { page: 3, pages: 3, total: 5 },
      },
    });

    const { result } = renderHook(() => useInfiniteManifestations(20), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.hasNextPage).toBe(false);
  });
});
