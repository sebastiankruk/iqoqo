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
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import axios from "axios";
import * as api from "@/lib/api/client";
import { useProfile } from "@/lib/api/hooks";

/**
 * Creates an isolated React Query provider for each profile hook test.
 *
 * @returns A wrapper component backed by a fresh query client.
 */
function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  /**
   * Wraps a test hook with its query client provider.
   *
   * @param props - Wrapper props.
   * @param props.children - The hook test children.
   * @returns The provided child tree.
   */
  function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  }
  Wrapper.displayName = "ProfileHookTestWrapper";
  return Wrapper;
}

describe("useProfile error handling", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it.each([401, 404])("logs out for an Axios %i response", async status => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true } as Response);
    vi.spyOn(api, "apiFetch").mockRejectedValueOnce(
      Object.assign(new axios.AxiosError("request failed"), { response: { status } })
    );

    const { result } = renderHook(() => useProfile(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
    expect(fetchSpy).toHaveBeenCalledWith("/api/auth/logout", { method: "POST" });
  });

  it("does not log out for an unrelated failure", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true } as Response);
    vi.spyOn(api, "apiFetch").mockRejectedValueOnce(new Error("Token expired"));

    const { result } = renderHook(() => useProfile(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
