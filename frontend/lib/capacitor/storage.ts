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
export const SERVERS_STORAGE_KEY = "iqoqo_servers_v1";
export const ACTIVE_SERVER_ID_KEY = "iqoqo_active_server_id";

export interface ServerProfile {
  id: string;
  name: string;
  url: string;
  /** Reserved for v1.3.0 HASS-style local/LAN dual-URL mode (C159). */
  localUrl?: string;
  addedAt: string;
  lastUsedAt?: string;
}

let inMemoryInstanceUrl: string | null = null;
let inMemoryActiveServerId: string | null = null;

/** Generate a stable, URL-safe server profile ID. */
function generateServerId(url: string): string {
  const slug = url
    .replace(/^https?:\/\//i, "")
    .replace(/[^a-z0-9]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase()
    .slice(0, 24);
  const rand = Math.random().toString(36).slice(2, 8);
  return `srv-${slug || "iqoqo"}-${rand}`;
}

/** Normalize an instance URL by trimming whitespace and trailing slashes. */
function normalizeServerUrl(url: string): string {
  return url.trim().replace(/\/+$/, "");
}

/** Read a string key from Preferences (native) or localStorage (web). */
async function readPref(key: string): Promise<string | null> {
  if (isNativeApp()) {
    try {
      const { value } = await Preferences.get({ key });
      if (value !== undefined && value !== null) {
        return value;
      }
    } catch {
      // Fallback to localStorage
    }
  }
  if (typeof window !== "undefined") {
    try {
      return window.localStorage.getItem(key) || null;
    } catch {
      return null;
    }
  }
  return null;
}

/** Write a string key to localStorage mirror and native Preferences. */
async function writePref(key: string, value: string): Promise<void> {
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // Ignore storage quota errors
    }
  }
  if (isNativeApp()) {
    try {
      await Preferences.set({ key, value });
    } catch {
      // Ignore preferences errors
    }
  }
}

/** Remove a string key from localStorage mirror and native Preferences. */
async function removePref(key: string): Promise<void> {
  if (typeof window !== "undefined") {
    try {
      window.localStorage.removeItem(key);
    } catch {
      // Ignore
    }
  }
  if (isNativeApp()) {
    try {
      await Preferences.remove({ key });
    } catch {
      // Ignore
    }
  }
}

// Eagerly initialize cache from localStorage and native Preferences on module load
if (typeof window !== "undefined") {
  try {
    const val = window.localStorage.getItem(INSTANCE_URL_KEY);
    if (val) {
      inMemoryInstanceUrl = val.replace(/\/+$/, "");
    }
    const activeId = window.localStorage.getItem(ACTIVE_SERVER_ID_KEY);
    if (activeId) {
      inMemoryActiveServerId = activeId;
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
    Preferences.get({ key: ACTIVE_SERVER_ID_KEY })
      .then(({ value }) => {
        if (value) {
          inMemoryActiveServerId = value;
          try {
            window.localStorage.setItem(ACTIVE_SERVER_ID_KEY, value);
          } catch {
            // Ignore
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
 * Synchronously retrieves the active server profile ID from in-memory cache
 * or localStorage mirror.
 *
 * @returns {string | null} The active server ID or null if not set.
 */
export function getSyncActiveServerId(): string | null {
  if (inMemoryActiveServerId) {
    return inMemoryActiveServerId;
  }
  if (typeof window !== "undefined") {
    try {
      const val = window.localStorage.getItem(ACTIVE_SERVER_ID_KEY);
      if (val) {
        inMemoryActiveServerId = val;
        return val;
      }
    } catch {
      return null;
    }
  }
  return null;
}

/**
 * Retrieve the saved server profiles list, migrating any legacy single-server
 * entry on first read.
 *
 * @returns {Promise<ServerProfile[]>} Saved server profiles.
 */
export async function getSavedServers(): Promise<ServerProfile[]> {
  const raw = await readPref(SERVERS_STORAGE_KEY);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed.filter((s): s is ServerProfile =>
          Boolean(s && typeof s.id === "string" && typeof s.url === "string")
        );
      }
    } catch {
      // Fall through to legacy migration
    }
  }

  return await migrateLegacyServerStorage();
}

/**
 * Idempotently migrate legacy single-server keys (`iqoqo_instance_url`,
 * `iqoqo_instance_name`, `iqoqo_auth_token`) into `ServerProfile[0]`.
 *
 * @returns {Promise<ServerProfile[]>} Migrated server profiles (or empty array).
 */
export async function migrateLegacyServerStorage(): Promise<ServerProfile[]> {
  const legacyUrl = await readPref(INSTANCE_URL_KEY);
  if (!legacyUrl) {
    return [];
  }
  const normalizedUrl = normalizeServerUrl(legacyUrl);
  if (!normalizedUrl) {
    return [];
  }

  const legacyName = (await readPref(INSTANCE_NAME_KEY)) || "iqoqo Library";
  const now = new Date().toISOString();
  const profile: ServerProfile = {
    id: generateServerId(normalizedUrl),
    name: legacyName,
    url: normalizedUrl,
    addedAt: now,
    lastUsedAt: now,
  };

  await writePref(SERVERS_STORAGE_KEY, JSON.stringify([profile]));
  inMemoryActiveServerId = profile.id;
  await writePref(ACTIVE_SERVER_ID_KEY, profile.id);

  // Migrate legacy auth token into the server-scoped SecureStorage key and remove legacy key
  const legacyToken = await readSecureToken(AUTH_TOKEN_KEY);
  if (legacyToken) {
    await writeSecureToken(tokenKeyForServer(profile.id), legacyToken);
    await removeSecureToken(AUTH_TOKEN_KEY);
  }

  return [profile];
}

/**
 * Resolve the active server profile ID.
 *
 * @returns {Promise<string | null>} Active server ID or null.
 */
export async function getActiveServerId(): Promise<string | null> {
  const stored = await readPref(ACTIVE_SERVER_ID_KEY);
  if (stored) {
    inMemoryActiveServerId = stored;
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(ACTIVE_SERVER_ID_KEY, stored);
      } catch {
        // Ignore localStorage mirror errors
      }
    }
    return stored;
  }
  inMemoryActiveServerId = null;
  return null;
}

/**
 * Add or update a server profile and optionally mark it active.
 *
 * @param {object} input - Server profile details
 * @param {string} input.url - Instance base URL
 * @param {string} [input.name] - Optional display name
 * @param {string} [input.localUrl] - Optional local network URL (reserved for v1.3.0)
 * @param {boolean} [activate] - Whether to set this server active immediately
 * @returns {Promise<ServerProfile>} The saved server profile
 */
export async function saveServerProfile(
  input: { url: string; name?: string; localUrl?: string },
  activate = true
): Promise<ServerProfile> {
  const normalizedUrl = normalizeServerUrl(input.url);
  const displayName = (input.name || "iqoqo Library").trim() || "iqoqo Library";
  const now = new Date().toISOString();
  const servers = await getSavedServers();
  const existingIdx = servers.findIndex(s => normalizeServerUrl(s.url) === normalizedUrl);

  let profile: ServerProfile;
  if (existingIdx >= 0) {
    profile = {
      ...servers[existingIdx],
      name: input.name ? displayName : servers[existingIdx].name,
      url: normalizedUrl,
      ...(input.localUrl !== undefined ? { localUrl: normalizeServerUrl(input.localUrl) || undefined } : {}),
      lastUsedAt: activate ? now : servers[existingIdx].lastUsedAt,
    };
    servers[existingIdx] = profile;
  } else {
    profile = {
      id: generateServerId(normalizedUrl),
      name: displayName,
      url: normalizedUrl,
      ...(input.localUrl ? { localUrl: normalizeServerUrl(input.localUrl) } : {}),
      addedAt: now,
      lastUsedAt: activate ? now : undefined,
    };
    servers.push(profile);
  }

  await writePref(SERVERS_STORAGE_KEY, JSON.stringify(servers));
  if (activate) {
    await switchActiveServer(profile.id, servers);
  }
  return profile;
}

/**
 * Rename or update an existing server profile.
 *
 * @param {string} serverId - Target server ID
 * @param {object} patch - Fields to update
 * @param {string} [patch.name] - Updated display name
 * @param {string} [patch.localUrl] - Updated local network URL
 * @returns {Promise<ServerProfile | null>} Updated profile or null if not found
 */
export async function updateServerProfile(
  serverId: string,
  patch: { name?: string; localUrl?: string }
): Promise<ServerProfile | null> {
  const servers = await getSavedServers();
  const idx = servers.findIndex(s => s.id === serverId);
  if (idx < 0) return null;

  const updated: ServerProfile = {
    ...servers[idx],
    ...(patch.name !== undefined && patch.name.trim() ? { name: patch.name.trim() } : {}),
    ...(patch.localUrl !== undefined ? { localUrl: normalizeServerUrl(patch.localUrl) || undefined } : {}),
  };
  servers[idx] = updated;
  await writePref(SERVERS_STORAGE_KEY, JSON.stringify(servers));

  const activeId = await getActiveServerId();
  if (activeId === serverId && patch.name?.trim()) {
    await setInstanceName(updated.name);
  }
  return updated;
}

/**
 * Switch the active server profile without wiping credentials or offline cache
 * of other saved servers.
 *
 * @param {string} serverId - Target server ID
 * @param {ServerProfile[]} preloadedServers - Optional preloaded list
 * @returns {Promise<ServerProfile | null>} Activated server profile or null
 */
export async function switchActiveServer(
  serverId: string,
  preloadedServers?: ServerProfile[]
): Promise<ServerProfile | null> {
  const servers = preloadedServers ?? (await getSavedServers());
  const idx = servers.findIndex(s => s.id === serverId);
  if (idx < 0) return null;

  const target = {
    ...servers[idx],
    lastUsedAt: new Date().toISOString(),
  };
  servers[idx] = target;

  inMemoryActiveServerId = target.id;
  await writePref(SERVERS_STORAGE_KEY, JSON.stringify(servers));
  await writePref(ACTIVE_SERVER_ID_KEY, target.id);
  await setInstanceUrl(target.url);
  await setInstanceName(target.name);
  return target;
}

/**
 * Remove a saved server profile along with its isolated auth token and offline cache.
 * If the removed server was active, activates the next available server (or clears active keys).
 *
 * @param {string} serverId - Server profile ID to remove
 * @returns {Promise<ServerProfile | null>} The new active server profile or null
 */
export async function removeServerProfile(serverId: string): Promise<ServerProfile | null> {
  const servers = await getSavedServers();
  const remaining = servers.filter(s => s.id !== serverId);
  await writePref(SERVERS_STORAGE_KEY, JSON.stringify(remaining));

  // Delete only the removed server's isolated credentials & offline cache
  await removeSecureToken(tokenKeyForServer(serverId));
  await clearOfflineCache(serverId);

  const activeId = await getActiveServerId();
  if (activeId === serverId) {
    if (remaining.length > 0) {
      return await switchActiveServer(remaining[0].id, remaining);
    }
    inMemoryActiveServerId = null;
    await removePref(ACTIVE_SERVER_ID_KEY);
    await removeInstanceUrl();
    await removeInstanceName();
    return null;
  }

  return remaining.find(s => s.id === activeId) || null;
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
  const normalized = normalizeServerUrl(url);
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

/** Build the per-server SecureStorage / localStorage token key. */
function tokenKeyForServer(serverId: string | null): string {
  return serverId ? `${AUTH_TOKEN_KEY}_${serverId}` : AUTH_TOKEN_KEY;
}

/** Read a token from hardware-backed SecureStorage (native) or localStorage (web). */
async function readSecureToken(key: string): Promise<string | null> {
  if (isNativeApp()) {
    try {
      const result = await SecureStoragePlugin.get({ key });
      return result?.value || null;
    } catch {
      return null;
    }
  }
  if (typeof window !== "undefined") {
    return window.localStorage.getItem(key) || null;
  }
  return null;
}

/** Write a token to hardware-backed SecureStorage (native) or localStorage (web). */
async function writeSecureToken(key: string, token: string): Promise<void> {
  if (isNativeApp()) {
    await SecureStoragePlugin.set({ key, value: token });
  } else if (typeof window !== "undefined") {
    window.localStorage.setItem(key, token);
  }
}

/** Remove a token from hardware-backed SecureStorage (native) or localStorage (web). */
async function removeSecureToken(key: string): Promise<void> {
  if (isNativeApp()) {
    try {
      await SecureStoragePlugin.remove({ key });
    } catch {
      // Ignore if not found
    }
  } else if (typeof window !== "undefined") {
    window.localStorage.removeItem(key);
  }
}

/**
 * Retrieve the authentication token for the active (or specified) server.
 * Uses hardware-backed secure storage on iOS Keychain / Android Keystore.
 *
 * @param {string} serverId - Optional target server ID
 * @returns {Promise<string | null>} The authentication token or null.
 */
export async function getAuthToken(serverId?: string): Promise<string | null> {
  const targetId = serverId ?? (await getActiveServerId());
  return await readSecureToken(tokenKeyForServer(targetId));
}

/**
 * Store the authentication token in hardware-encrypted secure storage
 * scoped to the active (or specified) server.
 *
 * @param {string} token - The session JWT or PAT
 * @param {string} serverId - Optional target server ID
 * @returns {Promise<void>}
 */
export async function setAuthToken(token: string, serverId?: string): Promise<void> {
  const targetId = serverId ?? (await getActiveServerId());
  await writeSecureToken(tokenKeyForServer(targetId), token);
}

/**
 * Remove the stored authentication token for the active (or specified) server.
 *
 * @param {string} serverId - Optional target server ID
 * @returns {Promise<void>}
 */
export async function removeAuthToken(serverId?: string): Promise<void> {
  const targetId = serverId ?? (await getActiveServerId());
  await clearOfflineCache(targetId ?? undefined);
  await removeSecureToken(tokenKeyForServer(targetId));
  if (!serverId && targetId) {
    await removeSecureToken(AUTH_TOKEN_KEY);
  }
}

export const clearAuthToken = removeAuthToken;

/**
 * Wipe all mobile credentials, server profiles, and instance settings.
 *
 * @returns {Promise<void>}
 */
export async function clearAllMobileStorage(): Promise<void> {
  const servers = await getSavedServers().catch(() => [] as ServerProfile[]);
  for (const srv of servers) {
    await clearOfflineCache(srv.id);
    await removeSecureToken(tokenKeyForServer(srv.id));
  }
  inMemoryInstanceUrl = null;
  inMemoryActiveServerId = null;
  await clearOfflineCache();
  await removeSecureToken(AUTH_TOKEN_KEY);
  await removePref(SERVERS_STORAGE_KEY);
  await removePref(ACTIVE_SERVER_ID_KEY);
  await removeInstanceUrl();
  await removeInstanceName();
}
