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
  getSyncInstanceUrl,
  setInstanceUrl,
  removeInstanceUrl,
  getInstanceName,
  setInstanceName,
  getAuthToken,
  setAuthToken,
  removeAuthToken,
  clearAllMobileStorage,
  getSavedServers,
  saveServerProfile,
  switchActiveServer,
  updateServerProfile,
  removeServerProfile,
  getActiveServerId,
  getSyncActiveServerId,
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
    vi.mocked(Preferences.get).mockResolvedValue({ value: null });
    vi.mocked(Preferences.set).mockResolvedValue();
    vi.mocked(Preferences.remove).mockResolvedValue();
  });

  describe("Native Device Environment", () => {
    beforeEach(() => {
      vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    });

    it("stores and retrieves instance URL via Preferences without trailing slash", async () => {
      vi.mocked(Preferences.get).mockResolvedValueOnce({ value: "https://iqoqo.kruk.cc/" });

      await setInstanceUrl("https://iqoqo.kruk.cc/");
      expect(Preferences.set).toHaveBeenCalledWith({
        key: INSTANCE_URL_KEY,
        value: "https://iqoqo.kruk.cc",
      });

      const url = await getInstanceUrl();
      expect(url).toBe("https://iqoqo.kruk.cc");
      expect(getSyncInstanceUrl()).toBe("https://iqoqo.kruk.cc");
    });

    it("clears synchronous instance URL when removeInstanceUrl or clearAllMobileStorage runs", async () => {
      await setInstanceUrl("https://preview.iqoqo.cc");
      expect(getSyncInstanceUrl()).toBe("https://preview.iqoqo.cc");

      await removeInstanceUrl();
      expect(getSyncInstanceUrl()).toBeNull();

      await setInstanceUrl("https://preview.iqoqo.cc");
      expect(getSyncInstanceUrl()).toBe("https://preview.iqoqo.cc");

      await clearAllMobileStorage();
      expect(getSyncInstanceUrl()).toBeNull();
    });

    it("stores and retrieves instance display name via Preferences", async () => {
      vi.mocked(Preferences.get).mockResolvedValueOnce({ value: "My Home Library" });

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

    it("namespaces native SecureStoragePlugin tokens and Preferences across multi-server profiles", async () => {
      const prefMap = new Map<string, string>();
      const secMap = new Map<string, string>();

      vi.mocked(Preferences.get).mockImplementation(async ({ key }) => ({ value: prefMap.get(key) ?? null }));
      vi.mocked(Preferences.set).mockImplementation(async ({ key, value }) => {
        prefMap.set(key, value);
      });
      vi.mocked(Preferences.remove).mockImplementation(async ({ key }) => {
        prefMap.delete(key);
      });

      vi.mocked(SecureStoragePlugin.get).mockImplementation(async ({ key }) => {
        if (!secMap.has(key)) throw new Error("not found");
        return { value: secMap.get(key)! };
      });
      vi.mocked(SecureStoragePlugin.set).mockImplementation(async ({ key, value }) => {
        secMap.set(key, value);
        return { value: true };
      });
      vi.mocked(SecureStoragePlugin.remove).mockImplementation(async ({ key }) => {
        secMap.delete(key);
        return { value: true };
      });

      const srvA = await saveServerProfile({ url: "https://one.iqoqo.cc", name: "One" }, true);
      await setAuthToken("native-tok-1");
      const srvB = await saveServerProfile({ url: "https://two.iqoqo.cc", name: "Two" }, true);
      await setAuthToken("native-tok-2");

      expect(await getAuthToken(srvA.id)).toBe("native-tok-1");
      expect(await getAuthToken(srvB.id)).toBe("native-tok-2");

      await switchActiveServer(srvA.id);
      expect(await getActiveServerId()).toBe(srvA.id);
      expect(await getAuthToken()).toBe("native-tok-1");

      await removeServerProfile(srvB.id);
      expect(await getAuthToken(srvB.id)).toBeNull();
      expect(await getAuthToken(srvA.id)).toBe("native-tok-1");

      await clearAllMobileStorage();
      expect(await getSavedServers()).toEqual([]);
      expect(await getAuthToken(srvA.id)).toBeNull();
    });

    it("resolves active server asynchronously on cold start after localStorage eviction", async () => {
      vi.mocked(Preferences.get).mockImplementation(async ({ key }) => ({
        value: key === "iqoqo_active_server_id" ? "srv-cold" : null,
      }));
      vi.mocked(SecureStoragePlugin.set).mockResolvedValue({ value: true });
      vi.mocked(SecureStoragePlugin.get).mockResolvedValue({ value: "cold-tok" });
      vi.mocked(SecureStoragePlugin.remove).mockResolvedValue({ value: true });

      expect(window.localStorage.length).toBe(0);

      await setAuthToken("cold-tok");
      expect(SecureStoragePlugin.set).toHaveBeenCalledWith({
        key: `${AUTH_TOKEN_KEY}_srv-cold`,
        value: "cold-tok",
      });

      expect(await getAuthToken()).toBe("cold-tok");
      expect(SecureStoragePlugin.get).toHaveBeenCalledWith({ key: `${AUTH_TOKEN_KEY}_srv-cold` });
      expect(SecureStoragePlugin.get).not.toHaveBeenCalledWith({ key: AUTH_TOKEN_KEY });

      await removeAuthToken();
      expect(SecureStoragePlugin.remove).toHaveBeenCalledWith({ key: `${AUTH_TOKEN_KEY}_srv-cold` });
    });

    it("never leaks legacy un-scoped token to active server without scoped token and cleans legacy key on logout", async () => {
      const prefMap = new Map<string, string>();
      const secMap = new Map<string, string>();
      secMap.set(AUTH_TOKEN_KEY, "stale-legacy-token");

      vi.mocked(Preferences.get).mockImplementation(async ({ key }) => ({ value: prefMap.get(key) ?? null }));
      vi.mocked(Preferences.set).mockImplementation(async ({ key, value }) => {
        prefMap.set(key, value);
      });
      vi.mocked(Preferences.remove).mockImplementation(async ({ key }) => {
        prefMap.delete(key);
      });
      vi.mocked(SecureStoragePlugin.get).mockImplementation(async ({ key }) => {
        if (!secMap.has(key)) throw new Error("not found");
        return { value: secMap.get(key)! };
      });
      vi.mocked(SecureStoragePlugin.set).mockImplementation(async ({ key, value }) => {
        secMap.set(key, value);
        return { value: true };
      });
      vi.mocked(SecureStoragePlugin.remove).mockImplementation(async ({ key }) => {
        secMap.delete(key);
        return { value: true };
      });

      const srvB = await saveServerProfile({ url: "https://server-b.iqoqo.cc", name: "Server B" }, true);
      expect(await getAuthToken()).toBeNull();

      await setAuthToken("srv-b-token");
      expect(await getAuthToken()).toBe("srv-b-token");

      await removeAuthToken();
      expect(secMap.has(`${AUTH_TOKEN_KEY}_${srvB.id}`)).toBe(false);
      expect(secMap.has(AUTH_TOKEN_KEY)).toBe(false);
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

    it("migrates legacy single-server keys and isolates tokens across multiple servers", async () => {
      await setInstanceUrl("https://prod.iqoqo.cc");
      await setInstanceName("Prod Library");
      await setAuthToken("prod-token-123");

      const migrated = await getSavedServers();
      expect(migrated).toHaveLength(1);
      expect(migrated[0].url).toBe("https://prod.iqoqo.cc");
      expect(migrated[0].name).toBe("Prod Library");
      const prodId = migrated[0].id;
      expect(getSyncActiveServerId()).toBe(prodId);
      expect(await getAuthToken(prodId)).toBe("prod-token-123");

      // Add second server and store isolated token
      const preview = await saveServerProfile({ url: "https://pre.iqoqo.cc", name: "Preview" }, true);
      await setAuthToken("preview-token-456");

      expect(await getActiveServerId()).toBe(preview.id);
      expect(await getAuthToken()).toBe("preview-token-456");
      expect(await getAuthToken(prodId)).toBe("prod-token-123");

      // Switch back to prod without losing preview token
      await switchActiveServer(prodId);
      expect(await getInstanceUrl()).toBe("https://prod.iqoqo.cc");
      expect(await getAuthToken()).toBe("prod-token-123");
      expect(await getAuthToken(preview.id)).toBe("preview-token-456");

      // Rename preview server
      const renamed = await updateServerProfile(preview.id, { name: "Staging" });
      expect(renamed?.name).toBe("Staging");

      // Remove preview server; prod remains intact
      await removeServerProfile(preview.id);
      expect(await getSavedServers()).toHaveLength(1);
      expect(await getAuthToken(preview.id)).toBeNull();
      expect(await getAuthToken(prodId)).toBe("prod-token-123");
    });
  });
});
