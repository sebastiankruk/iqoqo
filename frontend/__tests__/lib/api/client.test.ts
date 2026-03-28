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
 * Tests for the API client utilities: apiClient and apiFetch.
 *
 * axios is NOT mocked here – we inspect the axios instance configuration
 * directly. For network-level assertions (actual requests) we rely on the
 * backend integration tests in tests/test_phase2_frontend.py.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Set env before importing client so the baseURL is built correctly.
const ORIGINAL_ENV = process.env.NEXT_PUBLIC_API_URL;

describe("apiClient configuration", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    if (ORIGINAL_ENV === undefined) {
      delete process.env.NEXT_PUBLIC_API_URL;
    } else {
      process.env.NEXT_PUBLIC_API_URL = ORIGINAL_ENV;
    }
  });

  it("always uses the relative /api base URL (browser same-origin proxy)", async () => {
    // The client-side axios instance always uses a relative path so that
    // requests are same-origin and flow through the Next.js rewrite proxy.
    // NEXT_PUBLIC_API_URL is no longer read by the browser client – the
    // Next.js rewrite uses it server-side to forward to Flask.
    process.env.NEXT_PUBLIC_API_URL = "http://my-server:8080/api";
    const { apiClient } = await import("@/lib/api/client");
    expect(apiClient.defaults.baseURL as string).toBe("/api");
  });

  it("uses /api regardless of whether NEXT_PUBLIC_API_URL is set", async () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    const { apiClient } = await import("@/lib/api/client");
    expect(apiClient.defaults.baseURL as string).toBe("/api");
  });

  it("sets Content-Type to application/json by default", async () => {
    const { apiClient } = await import("@/lib/api/client");
    expect(apiClient.defaults.headers["Content-Type"]).toBe("application/json");
  });
});

describe("apiFetch helper", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("unwraps the data field from a successful ApiResponse envelope", async () => {
    const { apiFetch, apiClient } = await import("@/lib/api/client");

    // Spy on apiClient.get and return a mock envelope.
    vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: true, data: { id: 1, title: "Dune" }, error: null },
    } as never);

    const result = await apiFetch<{ id: number; title: string }>("/items/1");
    expect(result).toEqual({ id: 1, title: "Dune" });
  });

  it("throws when the envelope reports success:false", async () => {
    const { apiFetch, apiClient } = await import("@/lib/api/client");

    vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: false, data: null, error: "Not found" },
    } as never);

    await expect(apiFetch("/items/999")).rejects.toThrow("Not found");
  });

  it("throws a fallback message when error field is null on failure", async () => {
    const { apiFetch, apiClient } = await import("@/lib/api/client");

    vi.spyOn(apiClient, "get").mockResolvedValueOnce({
      data: { success: false, data: null, error: null },
    } as never);

    await expect(apiFetch("/items/999")).rejects.toThrow("Unknown error");
  });
});
