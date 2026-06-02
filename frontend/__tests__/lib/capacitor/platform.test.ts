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
 * Unit tests for frontend/lib/capacitor/platform.ts
 *
 * The Capacitor runtime does not exist in jsdom, so we mock @capacitor/core
 * and exercise every exported function.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

// Shared mock state.
let mockPlatform = "web";
let mockIsNative = false;

vi.mock("@capacitor/core", () => ({
  Capacitor: {
    getPlatform: () => mockPlatform,
    isNativePlatform: () => mockIsNative,
  },
}));

describe("platform utilities", () => {
  beforeEach(async () => {
    vi.resetModules();
    mockPlatform = "web";
    mockIsNative = false;
  });

  it("getPlatform returns 'web' in jsdom", async () => {
    const { getPlatform } = await import("@/lib/capacitor/platform");
    expect(getPlatform()).toBe("web");
  });

  it("isNativeApp returns false in jsdom", async () => {
    const { isNativeApp } = await import("@/lib/capacitor/platform");
    expect(isNativeApp()).toBe(false);
  });

  it("isIOS returns true when platform is 'ios'", async () => {
    mockPlatform = "ios";
    mockIsNative = true;
    const { isIOS } = await import("@/lib/capacitor/platform");
    expect(isIOS()).toBe(true);
  });

  it("isAndroid returns true when platform is 'android'", async () => {
    mockPlatform = "android";
    mockIsNative = true;
    const { isAndroid } = await import("@/lib/capacitor/platform");
    expect(isAndroid()).toBe(true);
  });

  it("isIOS returns false when platform is 'android'", async () => {
    mockPlatform = "android";
    const { isIOS } = await import("@/lib/capacitor/platform");
    expect(isIOS()).toBe(false);
  });

  it("isAndroid returns false when platform is 'ios'", async () => {
    mockPlatform = "ios";
    const { isAndroid } = await import("@/lib/capacitor/platform");
    expect(isAndroid()).toBe(false);
  });
});
