// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api/client";
import { useFacetStats } from "@/lib/api/hooks";

describe("useFacetStats API contract", () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  /**
   * Provides an isolated query cache for each hook test.
   * @param props - The wrapper properties.
   * @param props.children - The hook test tree.
   * @returns A React Query provider for the test tree.
   */
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  beforeEach(() => {
    queryClient.clear();
    vi.restoreAllMocks();
  });

  it("reads nonzero facet counts from the stats/facets API envelope and forwards filters", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          category_counts: { text: 3 },
          format_counts: { book: 2 },
          status_counts: { available: 2 },
          collection_counts: {},
          tag_counts: {},
          genre_counts: { Fiction: 2 },
          publisher_counts: {},
        },
        error: null,
      },
    } as never);

    const { result } = renderHook(() => useFacetStats("user", { scope: "user", view: "items", genres: "Fiction" }), {
      wrapper: Wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(getSpy).toHaveBeenCalledWith("/stats/facets?scope=user&view=items&genres=Fiction");
    expect(result.current.data?.category_counts).toEqual({ text: 3 });
    expect(result.current.data?.genre_counts).toEqual({ Fiction: 2 });
  });

  it("preserves zero counts returned for genuinely empty facets", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          category_counts: {},
          format_counts: {},
          status_counts: { available: 0 },
          collection_counts: {},
          tag_counts: {},
          genre_counts: {},
          publisher_counts: {},
        },
        error: null,
      },
    } as never);

    const { result } = renderHook(() => useFacetStats("global", { scope: "global", view: "manifestations" }), {
      wrapper: Wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.category_counts).toEqual({});
    expect(result.current.data?.status_counts).toEqual({ available: 0 });
  });
});
