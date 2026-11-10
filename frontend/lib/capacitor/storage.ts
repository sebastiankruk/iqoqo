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
import { Preferences } from "@capacitor/preferences";
import { SecureStoragePlugin } from "capacitor-secure-storage-plugin";
import { isNativeApp } from "./platform";
import { clearOfflineCache } from "./offline-cache";

export const INSTANCE_URL_KEY = "iqoqo_instance_url";
export const INSTANCE_NAME_KEY = "iqoqo_instance_name";
export const AUTH_TOKEN_KEY = "iqoqo_auth_token";

let inMemoryInstanceUrl: string | null = null;

// Eagerly initialize cache from localStorage and native Preferences on module load
if (typeof window !== "undefined") {
  try {
    const val = window.localStorage.getItem(INSTANCE_URL_KEY);
    if (val) {
      inMemoryInstanceUrl = val.replace(/\/+$/, "");
    }
  } catch {
    // Ignore localStorage access failures in restricted environments
  }

  if (isNativeApp()) {
    Preferences.get({ key: INSTANCE_URL_KEY })
      .then(({ value }) => {
        if (value) {
          const norm = value.replace(/\/+$/, "");
          inMemoryInstanceUrl = norm;
          try {
            window.localStorage.setItem(INSTANCE_URL_KEY, norm);
          } catch {
            // Ignore localStorage mirror errors
          }
        }
      })
      .catch(() => {});
  }
}

/**
 * Synchronously retrieves the active instance URL from in-memory cache
 * or localStorage mirror.
 *
 * @returns {string | null} The active instance URL or null if not yet resolved.
 */
export function getSyncInstanceUrl(): string | null {
  if (inMemoryInstanceUrl) {
    return inMemoryInstanceUrl;
  }
  if (typeof window !== "undefined") {
    const val = window.localStorage.getItem(INSTANCE_URL_KEY);
    if (val) {
      inMemoryInstanceUrl = val.replace(/\/+$/, "");
      return inMemoryInstanceUrl;
    }
  }
  return null;
}

/**
 * Retrieve the saved self-hosted instance URL.
 *
 * @returns {Promise<string | null>} The instance URL or null if not set.
 */
export async function getInstanceUrl(): Promise<string | null> {
  let resolved: string | null = null;
  if (isNativeApp()) {
    const { value } = await Preferences.get({ key: INSTANCE_URL_KEY });
    resolved = value ? value.replace(/\/+$/, "") : null;
  } else if (typeof window !== "undefined") {
    resolved = window.localStorage.getItem(INSTANCE_URL_KEY) || null;
  }
  inMemoryInstanceUrl = resolved;
  if (typeof window !== "undefined" && resolved) {
    window.localStorage.setItem(INSTANCE_URL_KEY, resolved);
  }
  return resolved;
}

/**
 * Persist the target instance URL.
 *
 * @param {string} url - Validated instance URL
 * @returns {Promise<void>}
 */
export async function setInstanceUrl(url: string): Promise<void> {
  const normalized = url.trim().replace(/\/+$/, "");
  inMemoryInstanceUrl = normalized;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(INSTANCE_URL_KEY, normalized);
  }
  if (isNativeApp()) {
    await Preferences.set({ key: INSTANCE_URL_KEY, value: normalized });
  }
}

/**
 * Remove the saved instance URL.
 *
 * @returns {Promise<void>}
 */
export async function removeInstanceUrl(): Promise<void> {
  inMemoryInstanceUrl = null;
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(INSTANCE_URL_KEY);
  }
  if (isNativeApp()) {
    await Preferences.remove({ key: INSTANCE_URL_KEY });
  }
}

/**
 * Retrieve the saved self-hosted instance display name.
 *
 * @returns {Promise<string | null>} The instance name or null.
 */
export async function getInstanceName(): Promise<string | null> {
  if (isNativeApp()) {
    const { value } = await Preferences.get({ key: INSTANCE_NAME_KEY });
    return value || null;
  }
  if (typeof window !== "undefined") {
    return window.localStorage.getItem(INSTANCE_NAME_KEY) || null;
  }
  return null;
}

/**
 * Persist the target instance display name.
 *
 * @param {string} name - Instance display name
 * @returns {Promise<void>}
 */
export async function setInstanceName(name: string): Promise<void> {
  if (isNativeApp()) {
    await Preferences.set({ key: INSTANCE_NAME_KEY, value: name.trim() });
  } else if (typeof window !== "undefined") {
    window.localStorage.setItem(INSTANCE_NAME_KEY, name.trim());
  }
}

/**
 * Remove the saved instance display name.
 *
 * @returns {Promise<void>}
 */
export async function removeInstanceName(): Promise<void> {
  if (isNativeApp()) {
    await Preferences.remove({ key: INSTANCE_NAME_KEY });
  } else if (typeof window !== "undefined") {
    window.localStorage.removeItem(INSTANCE_NAME_KEY);
  }
}

/**
 * Retrieve the authentication token.
 * Uses hardware-backed secure storage on iOS Keychain / Android Keystore.
 *
 * @returns {Promise<string | null>} The authentication token or null.
 */
export async function getAuthToken(): Promise<string | null> {
  if (isNativeApp()) {
    try {
      const result = await SecureStoragePlugin.get({ key: AUTH_TOKEN_KEY });
      return result?.value || null;
    } catch {
      return null;
    }
  }
  if (typeof window !== "undefined") {
    return window.localStorage.getItem(AUTH_TOKEN_KEY) || null;
  }
  return null;
}

/**
 * Store the authentication token in hardware-encrypted secure storage.
 *
 * @param {string} token - The session JWT or PAT
 * @returns {Promise<void>}
 */
export async function setAuthToken(token: string): Promise<void> {
  if (isNativeApp()) {
    await SecureStoragePlugin.set({ key: AUTH_TOKEN_KEY, value: token });
  } else if (typeof window !== "undefined") {
    window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  }
}

/**
 * Remove the stored authentication token.
 *
 * @returns {Promise<void>}
 */
export async function removeAuthToken(): Promise<void> {
  await clearOfflineCache();
  if (isNativeApp()) {
    try {
      await SecureStoragePlugin.remove({ key: AUTH_TOKEN_KEY });
    } catch {
      // Ignore if not found
    }
  } else if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

/**
 * Wipe all mobile credentials and instance settings.
 *
 * @returns {Promise<void>}
 */
export async function clearAllMobileStorage(): Promise<void> {
  inMemoryInstanceUrl = null;
  await clearOfflineCache();
  await removeAuthToken();
  await removeInstanceUrl();
  await removeInstanceName();
}
