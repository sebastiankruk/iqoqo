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

  it("uses the NEXT_PUBLIC_API_URL env variable when set", async () => {
    // NEXT_PUBLIC_API_URL is the full base URL (including path prefix like /api).
    process.env.NEXT_PUBLIC_API_URL = "http://my-server:8080/api";
    const { apiClient } = await import("@/lib/api/client");
    expect((apiClient.defaults.baseURL as string)).toBe("http://my-server:8080/api");
  });

  it("falls back to localhost:5000 when the env variable is not set", async () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    const { apiClient } = await import("@/lib/api/client");
    expect((apiClient.defaults.baseURL as string)).toBe("http://localhost:5000/api");
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
