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

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { createAppQueryClient } from "@/components/providers";
import { useEscalationQueue, useMyEscalations } from "@/lib/api/escalations";
import { useWorkIntent } from "@/lib/api/hooks/intents";
import { useProfile } from "@/lib/api/hooks/user";

/**
 * Creates a wrapper that provides the given query client to a tested hook.
 *
 * @param client - The query client used by the test.
 * @returns A hook wrapper component.
 */
function makeWrapper(client: QueryClient) {
  /**
   * Provides the query client context.
   *
   * @param props - Wrapper properties.
   * @param props.children - The rendered hook tree.
   * @returns The wrapped children.
   */
  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children);
  }
  Wrapper.displayName = "QueryStalenessTestWrapper";
  return Wrapper;
}

/**
 * Reads the observer-specific stale time for an existing cached query.
 *
 * @param client - The query client containing the query.
 * @param queryKey - The key to inspect.
 * @returns The query stale time, if set.
 */
function getQueryStaleTime(client: QueryClient, queryKey: readonly unknown[]): number | undefined {
  const options = client.getQueryCache().find({ queryKey })?.options;
  return (options as { staleTime?: number } | undefined)?.staleTime;
}

describe("query staleness configuration", () => {
  it("uses a 60-second default stale time", () => {
    const client = createAppQueryClient();
    expect(client.getDefaultOptions().queries).toMatchObject({ staleTime: 60_000, retry: 1 });
  });

  it("keeps volatile profile and work-intent queries immediately stale", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrapper = makeWrapper(client);

    renderHook(() => useProfile(), { wrapper });
    renderHook(() => useWorkIntent(123), { wrapper });

    expect(getQueryStaleTime(client, ["profile"])).toBe(0);
    expect(getQueryStaleTime(client, ["workIntent", 123])).toBe(0);
  });

  it("uses 30-second stale times for personal and queue escalation queries", () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrapper = makeWrapper(client);

    renderHook(() => useMyEscalations(false), { wrapper });
    renderHook(() => useEscalationQueue("pending", false), { wrapper });

    expect(getQueryStaleTime(client, ["escalations", "mine"])).toBe(30_000);
    expect(
      getQueryStaleTime(client, ["escalations", "queue", "pending"])
    ).toBe(30_000);
  });

});
