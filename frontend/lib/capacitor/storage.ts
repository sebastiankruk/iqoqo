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
// SECURITY NOTE: Auth tokens are stored in capacitor-secure-storage-plugin
// (Keychain on iOS, EncryptedSharedPreferences on Android). Non-sensitive config
// (instance URL, name, locale) uses standard @capacitor/preferences.
import { Preferences } from "@capacitor/preferences";
import { SecureStoragePlugin } from "capacitor-secure-storage-plugin";

const INSTANCE_URL_KEY = "iqoqo_instance_url";
const INSTANCE_NAME_KEY = "iqoqo_instance_name";
const AUTH_TOKEN_KEY = "iqoqo_auth_token";

// ---------------------------------------------------------------------------
// Instance config — non-sensitive, standard Preferences
// ---------------------------------------------------------------------------

/**
 * Retrieve the stored iqoqo instance URL, or null if not yet configured.
 *
 * @returns {Promise<string | null>} The stored URL or null.
 */
export async function getInstanceUrl(): Promise<string | null> {
  const { value } = await Preferences.get({ key: INSTANCE_URL_KEY });
  return value;
}

/**
 * Persist the iqoqo instance URL.
 *
 * @param url - The base URL of the iqoqo backend (no trailing slash).
 */
export async function setInstanceUrl(url: string): Promise<void> {
  await Preferences.set({ key: INSTANCE_URL_KEY, value: url });
}

/**
 * Retrieve the human-readable name for the configured instance, or null.
 *
 * @returns {Promise<string | null>} The instance name or null.
 */
export async function getInstanceName(): Promise<string | null> {
  const { value } = await Preferences.get({ key: INSTANCE_NAME_KEY });
  return value;
}

/**
 * Persist the human-readable name for the configured instance.
 *
 * @param name - The display name of the instance.
 */
export async function setInstanceName(name: string): Promise<void> {
  await Preferences.set({ key: INSTANCE_NAME_KEY, value: name });
}

// ---------------------------------------------------------------------------
// Auth token — sensitive, encrypted secure storage
// ---------------------------------------------------------------------------

/**
 * Retrieve the stored auth token from platform-level encrypted storage.
 * Returns null if the key does not exist or the storage is unavailable.
 *
 * @returns {Promise<string | null>} The auth token or null.
 */
export async function getAuthToken(): Promise<string | null> {
  try {
    const { value } = await SecureStoragePlugin.get({ key: AUTH_TOKEN_KEY });
    return value;
  } catch {
    // Key not found or storage unavailable — treat as unauthenticated.
    return null;
  }
}

/**
 * Store an auth token in platform-level encrypted storage.
 *
 * @param token - The JWT auth token to store.
 */
export async function setAuthToken(token: string): Promise<void> {
  await SecureStoragePlugin.set({ key: AUTH_TOKEN_KEY, value: token });
}

/**
 * Remove the auth token from encrypted storage.
 * Safe to call even if the key does not exist.
 */
export async function clearAuthToken(): Promise<void> {
  try {
    await SecureStoragePlugin.remove({ key: AUTH_TOKEN_KEY });
  } catch {
    // Key may not exist — safe to ignore.
  }
}

/**
 * Clear ALL stored preferences and encrypted tokens (e.g. on logout or reset).
 */
export async function clearAllData(): Promise<void> {
  await Preferences.clear();
  await clearAuthToken();
}
