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
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Capacitor } from "@capacitor/core";
import { isNativeApp, getPlatform, isAndroid, isIOS } from "@/lib/capacitor/platform";

vi.mock("@capacitor/core", () => ({
  Capacitor: {
    isNativePlatform: vi.fn(),
    getPlatform: vi.fn(),
  },
}));

describe("Capacitor Platform Utility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("detects web platform when not native", () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(false);
    vi.mocked(Capacitor.getPlatform).mockReturnValue("web");

    expect(isNativeApp()).toBe(false);
    expect(getPlatform()).toBe("web");
    expect(isAndroid()).toBe(false);
    expect(isIOS()).toBe(false);
  });

  it("detects Android native platform correctly", () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    vi.mocked(Capacitor.getPlatform).mockReturnValue("android");

    expect(isNativeApp()).toBe(true);
    expect(getPlatform()).toBe("android");
    expect(isAndroid()).toBe(true);
    expect(isIOS()).toBe(false);
  });

  it("detects iOS native platform correctly", () => {
    vi.mocked(Capacitor.isNativePlatform).mockReturnValue(true);
    vi.mocked(Capacitor.getPlatform).mockReturnValue("ios");

    expect(isNativeApp()).toBe(true);
    expect(getPlatform()).toBe("ios");
    expect(isAndroid()).toBe(false);
    expect(isIOS()).toBe(true);
  });
});
