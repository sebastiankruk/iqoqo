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
 * Unit tests for frontend/lib/capacitor/storage.ts
 *
 * Both @capacitor/preferences and capacitor-secure-storage-plugin are
 * mocked with in-memory stores so no native runtime is required.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── In-memory mock stores ───────────────────────────────────────────────────

const prefStore: Record<string, string> = {};
const secureStore: Record<string, string> = {};

vi.mock("@capacitor/preferences", () => ({
  Preferences: {
    get: vi.fn(({ key }: { key: string }) => Promise.resolve({ value: prefStore[key] ?? null })),
    set: vi.fn(({ key, value }: { key: string; value: string }) => {
      prefStore[key] = value;
      return Promise.resolve();
    }),
    clear: vi.fn(() => {
      Object.keys(prefStore).forEach(k => delete prefStore[k]);
      return Promise.resolve();
    }),
  },
}));

vi.mock("capacitor-secure-storage-plugin", () => ({
  SecureStoragePlugin: {
    get: vi.fn(({ key }: { key: string }) => {
      if (!(key in secureStore)) throw new Error("Key not found");
      return Promise.resolve({ value: secureStore[key] });
    }),
    set: vi.fn(({ key, value }: { key: string; value: string }) => {
      secureStore[key] = value;
      return Promise.resolve();
    }),
    remove: vi.fn(({ key }: { key: string }) => {
      delete secureStore[key];
      return Promise.resolve();
    }),
  },
}));

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("Capacitor storage wrappers", () => {
  beforeEach(() => {
    vi.resetModules();
    Object.keys(prefStore).forEach(k => delete prefStore[k]);
    Object.keys(secureStore).forEach(k => delete secureStore[k]);
  });

  it("getInstanceUrl returns null when not set", async () => {
    const { getInstanceUrl } = await import("@/lib/capacitor/storage");
    expect(await getInstanceUrl()).toBeNull();
  });

  it("setInstanceUrl persists and getInstanceUrl retrieves the value", async () => {
    const { setInstanceUrl, getInstanceUrl } = await import("@/lib/capacitor/storage");
    await setInstanceUrl("https://library.example.com");
    expect(await getInstanceUrl()).toBe("https://library.example.com");
  });

  it("getInstanceName returns null when not set", async () => {
    const { getInstanceName } = await import("@/lib/capacitor/storage");
    expect(await getInstanceName()).toBeNull();
  });

  it("setInstanceName persists and getInstanceName retrieves the value", async () => {
    const { setInstanceName, getInstanceName } = await import("@/lib/capacitor/storage");
    await setInstanceName("My Library");
    expect(await getInstanceName()).toBe("My Library");
  });

  it("getAuthToken returns null when not set", async () => {
    const { getAuthToken } = await import("@/lib/capacitor/storage");
    expect(await getAuthToken()).toBeNull();
  });

  it("setAuthToken persists and getAuthToken retrieves the value", async () => {
    const { setAuthToken, getAuthToken } = await import("@/lib/capacitor/storage");
    await setAuthToken("jwt.token.here");
    expect(await getAuthToken()).toBe("jwt.token.here");
  });

  it("clearAuthToken removes the stored token", async () => {
    const { setAuthToken, clearAuthToken, getAuthToken } = await import("@/lib/capacitor/storage");
    await setAuthToken("jwt.token.here");
    await clearAuthToken();
    expect(await getAuthToken()).toBeNull();
  });

  it("clearAllData removes all preferences and auth token", async () => {
    const { setInstanceUrl, setAuthToken, clearAllData, getInstanceUrl, getAuthToken } =
      await import("@/lib/capacitor/storage");
    await setInstanceUrl("https://library.example.com");
    await setAuthToken("jwt.token.here");
    await clearAllData();
    expect(await getInstanceUrl()).toBeNull();
    expect(await getAuthToken()).toBeNull();
  });
});
