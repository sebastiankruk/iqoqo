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

import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthProviders, fetchAuthProviders } from "@/hooks/use-auth-providers";
import * as platform from "@/lib/capacitor/platform";
import * as storage from "@/lib/capacitor/storage";
import React from "react";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  Wrapper.displayName = "QueryClientTestWrapper";
  return Wrapper;
};

describe("useAuthProviders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns google: true when API reports google enabled", async () => {
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ google: true, apple: false }),
    });

    const { result } = renderHook(() => useAuthProviders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual({ google: true, apple: false });
  });

  it("returns google: false and apple: false when API reports disabled", async () => {
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ google: false, apple: false }),
    });

    const { result } = renderHook(() => useAuthProviders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual({ google: false, apple: false });
  });

  it("returns apple: true when API reports apple enabled", async () => {
    (global.fetch as Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ google: false, apple: true }),
    });

    const { result } = renderHook(() => useAuthProviders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual({ google: false, apple: true });
  });

  it("falls back to false when API request fails", async () => {
    (global.fetch as Mock).mockRejectedValueOnce(new Error("Network error"));

    const providers = await fetchAuthProviders();
    expect(providers).toEqual({ google: false, apple: false });
  });

  it("resolves full instance URL when running inside native app", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    vi.spyOn(storage, "getSyncInstanceUrl").mockReturnValue("https://preview.iqoqo.cc");
    vi.spyOn(storage, "getInstanceUrl").mockResolvedValue("https://preview.iqoqo.cc");

    (global.fetch as Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ google: true, apple: false }),
    });

    const providers = await fetchAuthProviders();
    expect(global.fetch).toHaveBeenCalledWith("https://preview.iqoqo.cc/api/auth/providers");
    expect(providers).toEqual({ google: true, apple: false });
  });
});
