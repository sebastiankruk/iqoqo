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

export const INSTANCE_URL_KEY = "iqoqo_instance_url";
export const INSTANCE_NAME_KEY = "iqoqo_instance_name";
export const AUTH_TOKEN_KEY = "iqoqo_auth_token";

/**
 * Retrieve the saved self-hosted instance URL.
 *
 * @returns {Promise<string | null>} The instance URL or null if not set.
 */
export async function getInstanceUrl(): Promise<string | null> {
  if (isNativeApp()) {
    const { value } = await Preferences.get({ key: INSTANCE_URL_KEY });
    return value ? value.replace(/\/+$/, "") : null;
  }
  if (typeof window !== "undefined") {
    return window.localStorage.getItem(INSTANCE_URL_KEY) || null;
  }
  return null;
}

/**
 * Persist the target instance URL.
 *
 * @param {string} url - Validated instance URL
 * @returns {Promise<void>}
 */
export async function setInstanceUrl(url: string): Promise<void> {
  const normalized = url.trim().replace(/\/+$/, "");
  if (isNativeApp()) {
    await Preferences.set({ key: INSTANCE_URL_KEY, value: normalized });
  } else if (typeof window !== "undefined") {
    window.localStorage.setItem(INSTANCE_URL_KEY, normalized);
  }
}

/**
 * Remove the saved instance URL.
 *
 * @returns {Promise<void>}
 */
export async function removeInstanceUrl(): Promise<void> {
  if (isNativeApp()) {
    await Preferences.remove({ key: INSTANCE_URL_KEY });
  } else if (typeof window !== "undefined") {
    window.localStorage.removeItem(INSTANCE_URL_KEY);
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
  await removeAuthToken();
  await removeInstanceUrl();
  await removeInstanceName();
}
