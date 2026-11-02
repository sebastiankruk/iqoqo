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
import { Preferences } from "@capacitor/preferences";
import { SecureStoragePlugin } from "capacitor-secure-storage-plugin";
import * as platform from "@/lib/capacitor/platform";
import {
  getInstanceUrl,
  setInstanceUrl,
  getInstanceName,
  setInstanceName,
  getAuthToken,
  setAuthToken,
  removeAuthToken,
  clearAllMobileStorage,
  AUTH_TOKEN_KEY,
  INSTANCE_URL_KEY,
  INSTANCE_NAME_KEY,
} from "@/lib/capacitor/storage";

vi.mock("@capacitor/preferences", () => ({
  Preferences: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
  },
}));

vi.mock("capacitor-secure-storage-plugin", () => ({
  SecureStoragePlugin: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
    clear: vi.fn(),
  },
}));

describe("Capacitor Split Storage Utility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  describe("Native Device Environment", () => {
    beforeEach(() => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    });

    it("stores and retrieves instance URL via Preferences without trailing slash", async () => {
      vi.mocked(Preferences.get).mockResolvedValue({ value: "https://iqoqo.kruk.cc/" });

      await setInstanceUrl("https://iqoqo.kruk.cc/");
      expect(Preferences.set).toHaveBeenCalledWith({
        key: INSTANCE_URL_KEY,
        value: "https://iqoqo.kruk.cc",
      });

      const url = await getInstanceUrl();
      expect(url).toBe("https://iqoqo.kruk.cc");
    });

    it("stores and retrieves instance display name via Preferences", async () => {
      vi.mocked(Preferences.get).mockResolvedValue({ value: "My Home Library" });

      await setInstanceName("My Home Library");
      expect(Preferences.set).toHaveBeenCalledWith({
        key: INSTANCE_NAME_KEY,
        value: "My Home Library",
      });

      const name = await getInstanceName();
      expect(name).toBe("My Home Library");
    });

    it("stores auth token exclusively in hardware-backed SecureStoragePlugin and never Preferences", async () => {
      vi.mocked(SecureStoragePlugin.set).mockResolvedValue({ value: true });

      await setAuthToken("jwt-token-xyz");

      expect(SecureStoragePlugin.set).toHaveBeenCalledWith({
        key: AUTH_TOKEN_KEY,
        value: "jwt-token-xyz",
      });
      expect(Preferences.set).not.toHaveBeenCalledWith(expect.objectContaining({ key: AUTH_TOKEN_KEY }));
    });

    it("retrieves auth token from SecureStoragePlugin and returns null on rejection", async () => {
      vi.mocked(SecureStoragePlugin.get).mockResolvedValue({ value: "jwt-token-xyz" });
      const token = await getAuthToken();
      expect(token).toBe("jwt-token-xyz");

      vi.mocked(SecureStoragePlugin.get).mockRejectedValue(new Error("Key not found"));
      const missingToken = await getAuthToken();
      expect(missingToken).toBeNull();
    });

    it("clears all credentials and instance settings on reset", async () => {
      await clearAllMobileStorage();

      expect(SecureStoragePlugin.remove).toHaveBeenCalledWith({ key: AUTH_TOKEN_KEY });
      expect(Preferences.remove).toHaveBeenCalledWith({ key: INSTANCE_URL_KEY });
      expect(Preferences.remove).toHaveBeenCalledWith({ key: INSTANCE_NAME_KEY });
    });
  });

  describe("Web Browser Fallback Environment", () => {
    beforeEach(() => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(false);
    });

    it("stores instance URL and auth token in localStorage on web", async () => {
      await setInstanceUrl("https://demo.iqoqo.cc");
      expect(await getInstanceUrl()).toBe("https://demo.iqoqo.cc");

      await setAuthToken("web-mock-token");
      expect(await getAuthToken()).toBe("web-mock-token");

      await removeAuthToken();
      expect(await getAuthToken()).toBeNull();
    });
  });
});
