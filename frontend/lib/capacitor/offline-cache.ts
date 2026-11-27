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
import { isNativeApp } from "./platform";
import type { Item, WishlistItem, UserProfile } from "@/types/frbr";

export const OFFLINE_COLLECTION_CACHE_KEY = "iqoqo_offline_collection_snapshot";
export const OFFLINE_WISHLIST_CACHE_KEY = "iqoqo_offline_wishlist_snapshot";
export const OFFLINE_PROFILE_CACHE_KEY = "iqoqo_offline_profile_snapshot";
export const OFFLINE_MANUAL_QUEUE_KEY = "iqoqo_offline_manual_queue";

const ACTIVE_SERVER_ID_KEY = "iqoqo_active_server_id";

/**
 * Resolve a server-scoped offline cache key so multi-server profiles never
 * collide or overwrite each other's cached library snapshots.
 *
 * @param baseKey - Unscoped cache key constant
 * @param serverId - Optional explicit server profile ID
 * @returns Scoped key when a server ID is active, or `baseKey` otherwise
 */
export function scopedCacheKey(baseKey: string, serverId?: string): string {
  if (serverId) {
    return `${baseKey}_${serverId}`;
  }
  if (typeof window !== "undefined") {
    try {
      const activeId = window.localStorage.getItem(ACTIVE_SERVER_ID_KEY);
      if (activeId) {
        return `${baseKey}_${activeId}`;
      }
    } catch {
      // Ignore storage access failures
    }
  }
  return baseKey;
}

export interface OfflineCollectionSnapshot {
  timestamp: number;
  items: Item[];
}

export interface OfflineWishlistSnapshot {
  timestamp: number;
  items: WishlistItem[];
}

export interface OfflineProfileSnapshot {
  timestamp: number;
  profile: UserProfile;
}

export interface OfflineManualEntry {
  id: string; // client-generated uuid/timestamp
  timestamp: number;
  payload: {
    Title: string;
    Authors: string[];
    Format: string;
    ISBN?: string;
    PublicationDate?: string;
    Publisher?: string;
  };
}

/**
 * Save user profile snapshot to local storage for offline session preservation.
 *
 * @param profile - Active user profile
 */
export async function saveProfileSnapshot(profile: UserProfile, serverId?: string): Promise<void> {
  const key = scopedCacheKey(OFFLINE_PROFILE_CACHE_KEY, serverId);
  const payload: OfflineProfileSnapshot = {
    timestamp: Date.now(),
    profile,
  };
  const serialized = JSON.stringify(payload);

  if (isNativeApp()) {
    try {
      await Preferences.set({ key, value: serialized });
    } catch {
      // Ignore preferences write failure
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(key, serialized);
    } catch {
      // Ignore localStorage quotas
    }
  }
}

/**
 * Retrieve cached user profile snapshot if available.
 *
 * @param serverId - Optional target server ID
 * @returns Cached UserProfile or null
 */
export async function getCachedProfileSnapshot(serverId?: string): Promise<UserProfile | null> {
  const key = scopedCacheKey(OFFLINE_PROFILE_CACHE_KEY, serverId);
  let serialized: string | null = null;

  if (isNativeApp()) {
    try {
      const res = await Preferences.get({ key });
      serialized = res.value;
    } catch {
      serialized = null;
    }
  }

  if (!serialized && typeof window !== "undefined" && window.localStorage) {
    try {
      serialized = window.localStorage.getItem(key);
    } catch {
      serialized = null;
    }
  }

  if (!serialized) {
    return null;
  }

  try {
    const parsed = JSON.parse(serialized) as OfflineProfileSnapshot;
    if (parsed && parsed.profile && (parsed.profile.id || parsed.profile.email)) {
      return parsed.profile;
    }
  } catch {
    // Malformed JSON
  }
  return null;
}

/**
 * Save user collection snapshot to local storage for offline read-only querying.
 *
 * @param items - Array of physical collection items
 */
export async function saveCollectionSnapshot(items: Item[], serverId?: string): Promise<void> {
  const key = scopedCacheKey(OFFLINE_COLLECTION_CACHE_KEY, serverId);
  const payload: OfflineCollectionSnapshot = {
    timestamp: Date.now(),
    items,
  };
  const serialized = JSON.stringify(payload);

  if (isNativeApp()) {
    try {
      await Preferences.set({ key, value: serialized });
    } catch {
      // Ignore preferences write failure
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(key, serialized);
    } catch {
      // Ignore localStorage quotas / private browsing errors
    }
  }
}

/**
 * Retrieve cached collection snapshot if available.
 *
 * @param serverId - Optional target server ID
 * @returns Offline collection snapshot or null
 */
export async function getCachedCollectionSnapshot(serverId?: string): Promise<OfflineCollectionSnapshot | null> {
  const key = scopedCacheKey(OFFLINE_COLLECTION_CACHE_KEY, serverId);
  let serialized: string | null = null;

  if (isNativeApp()) {
    try {
      const res = await Preferences.get({ key });
      serialized = res.value;
    } catch {
      serialized = null;
    }
  }

  if (!serialized && typeof window !== "undefined" && window.localStorage) {
    try {
      serialized = window.localStorage.getItem(key);
    } catch {
      serialized = null;
    }
  }

  if (!serialized) {
    return null;
  }

  try {
    const parsed = JSON.parse(serialized) as OfflineCollectionSnapshot;
    if (parsed && Array.isArray(parsed.items)) {
      return parsed;
    }
  } catch {
    // Malformed JSON
  }
  return null;
}

/**
 * Save user wishlist snapshot to local storage for offline lookup.
 *
 * @param items - Array of wishlist items
 */
export async function saveWishlistSnapshot(items: WishlistItem[], serverId?: string): Promise<void> {
  const key = scopedCacheKey(OFFLINE_WISHLIST_CACHE_KEY, serverId);
  const payload: OfflineWishlistSnapshot = {
    timestamp: Date.now(),
    items,
  };
  const serialized = JSON.stringify(payload);

  if (isNativeApp()) {
    try {
      await Preferences.set({ key, value: serialized });
    } catch {
      // Ignore preferences write failure
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(key, serialized);
    } catch {
      // Ignore localStorage quotas
    }
  }
}

/**
 * Retrieve cached wishlist snapshot if available.
 *
 * @param serverId - Optional target server ID
 * @returns Offline wishlist snapshot or null
 */
export async function getCachedWishlistSnapshot(serverId?: string): Promise<OfflineWishlistSnapshot | null> {
  const key = scopedCacheKey(OFFLINE_WISHLIST_CACHE_KEY, serverId);
  let serialized: string | null = null;

  if (isNativeApp()) {
    try {
      const res = await Preferences.get({ key });
      serialized = res.value;
    } catch {
      serialized = null;
    }
  }

  if (!serialized && typeof window !== "undefined" && window.localStorage) {
    try {
      serialized = window.localStorage.getItem(key);
    } catch {
      serialized = null;
    }
  }

  if (!serialized) {
    return null;
  }

  try {
    const parsed = JSON.parse(serialized) as OfflineWishlistSnapshot;
    if (parsed && Array.isArray(parsed.items)) {
      return parsed;
    }
  } catch {
    // Malformed JSON
  }
  return null;
}

/**
 * Check if a barcode (ISBN, UPC, EAN) or title exists in the cached collection or wishlist.
 * Returns matching item or wishlist entry.
 *
 * @param query - Barcode or title search string
 */
export async function findOfflineDuplicate(
  query: string
): Promise<{ matchType: "collection" | "wishlist"; item: Item | WishlistItem } | null> {
  const normalized = query.trim().toLowerCase().replace(/[-\s]/g, "");
  if (!normalized) return null;

  const collection = await getCachedCollectionSnapshot();
  if (collection) {
    for (const item of collection.items) {
      const isbn = item.isbn?.replace(/[-\s]/g, "").toLowerCase();
      const barcode = item.local_barcode?.replace(/[-\s]/g, "").toLowerCase();
      const title = (item.title || "").toLowerCase();

      if (
        (isbn && isbn === normalized) ||
        (barcode && barcode === normalized) ||
        (title && title.includes(query.trim().toLowerCase()))
      ) {
        return { matchType: "collection", item };
      }
    }
  }

  const wishlist = await getCachedWishlistSnapshot();
  if (wishlist) {
    for (const entry of wishlist.items) {
      const title = (entry.title || entry.work?.title || "").toLowerCase();
      const isbn = entry.isbn?.replace(/[-\s]/g, "").toLowerCase();
      if ((isbn && isbn === normalized) || (title && title.includes(query.trim().toLowerCase()))) {
        return { matchType: "wishlist", item: entry };
      }
    }
  }

  return null;
}

/**
 * Retrieve the queued offline manual entries awaiting synchronization.
 *
 * @returns Array of queued offline manual scan entries
 */
export async function getOfflineManualQueue(serverId?: string): Promise<OfflineManualEntry[]> {
  const key = scopedCacheKey(OFFLINE_MANUAL_QUEUE_KEY, serverId);
  let serialized: string | null = null;

  if (isNativeApp()) {
    try {
      const res = await Preferences.get({ key });
      serialized = res.value;
    } catch {
      serialized = null;
    }
  }

  if (!serialized && typeof window !== "undefined" && window.localStorage) {
    try {
      serialized = window.localStorage.getItem(key);
    } catch {
      serialized = null;
    }
  }

  if (!serialized) return [];

  try {
    const parsed = JSON.parse(serialized);
    if (Array.isArray(parsed)) {
      return parsed as OfflineManualEntry[];
    }
  } catch {
    // Ignore malformed JSON
  }
  return [];
}

/**
 * Enqueue a manual item entry locally when offline and optimistically update cached snapshot.
 *
 * @param payload - The manual item payload submitted by the user
 * @returns The enqueued entry with timestamp and client id
 */
export async function enqueueOfflineManualEntry(payload: OfflineManualEntry["payload"]): Promise<OfflineManualEntry> {
  const queue = await getOfflineManualQueue();
  const entry: OfflineManualEntry = {
    id: `offline-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    timestamp: Date.now(),
    payload,
  };

  queue.push(entry);
  const serialized = JSON.stringify(queue);

  const queueKey = scopedCacheKey(OFFLINE_MANUAL_QUEUE_KEY);
  if (isNativeApp()) {
    try {
      await Preferences.set({ key: queueKey, value: serialized });
    } catch {
      // Ignore
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(queueKey, serialized);
    } catch {
      // Ignore
    }
  }

  // Optimistically add to cached collection snapshot
  const snapshot = await getCachedCollectionSnapshot();
  const provisionalItem: Item = {
    id: -entry.timestamp, // Negative ID marks provisional item
    manifestation_id: -entry.timestamp,
    owner_id: "offline_user",
    status: "read",
    collection_status: "available",
    title: payload.Title,
    authors: payload.Authors,
    isbn: payload.ISBN,
    local_barcode: payload.ISBN,
    publisher: payload.Publisher,
    content_type: payload.Format,
    added_at: new Date(entry.timestamp).toISOString(),
    updated_at: new Date(entry.timestamp).toISOString(),
    meta: {},
  };

  const existingItems = snapshot?.items || [];
  await saveCollectionSnapshot([provisionalItem, ...existingItems]);

  return entry;
}

let activeFlushPromise: Promise<{ synced: number; failed: number }> | null = null;

/**
 * Internal worker for flushing queued offline manual entries.
 */
async function _performFlushOfflineManualQueue(
  submitFn: (payload: OfflineManualEntry["payload"]) => Promise<unknown>
): Promise<{ synced: number; failed: number }> {
  const queue = await getOfflineManualQueue();
  if (queue.length === 0) return { synced: 0, failed: 0 };

  const remaining: OfflineManualEntry[] = [];
  const syncedTimestamps: number[] = [];
  let synced = 0;
  let failed = 0;

  for (const entry of queue) {
    try {
      await submitFn(entry.payload);
      synced++;
      syncedTimestamps.push(entry.timestamp);
    } catch (e) {
      console.warn("Failed to flush offline manual entry:", entry.id, e);
      failed++;
      remaining.push(entry);
    }
  }

  const serialized = JSON.stringify(remaining);
  const queueKey = scopedCacheKey(OFFLINE_MANUAL_QUEUE_KEY);
  if (isNativeApp()) {
    try {
      await Preferences.set({ key: queueKey, value: serialized });
    } catch {
      // Ignore
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(queueKey, serialized);
    } catch {
      // Ignore
    }
  }

  // Prune synced provisional negative-ID items from cached collection snapshot
  if (syncedTimestamps.length > 0) {
    try {
      const snapshot = await getCachedCollectionSnapshot();
      if (snapshot && snapshot.items.length > 0) {
        const syncedSet = new Set(syncedTimestamps.map(ts => -ts));
        const filteredItems = snapshot.items.filter(item => !syncedSet.has(item.id));
        if (filteredItems.length !== snapshot.items.length) {
          await saveCollectionSnapshot(filteredItems);
        }
      }
    } catch {
      // Ignore snapshot pruning errors
    }
  }

  return { synced, failed };
}

/**
 * Flush queued offline manual entries to the backend API.
 * Protected by an in-flight mutex to avoid concurrent duplicate submissions.
 *
 * @param submitFn - The async function that submits each payload to the server
 * @returns Counts of synced and failed items
 */
export function flushOfflineManualQueue(
  submitFn: (payload: OfflineManualEntry["payload"]) => Promise<unknown>
): Promise<{ synced: number; failed: number }> {
  if (activeFlushPromise) {
    return activeFlushPromise;
  }

  activeFlushPromise = (async () => {
    try {
      return await _performFlushOfflineManualQueue(submitFn);
    } finally {
      activeFlushPromise = null;
    }
  })();

  return activeFlushPromise;
}

/**
 * Purge all cached collection, wishlist, profile, and manual queue offline records.
 * Called on logout, server removal, or explicit cache clearance.
 *
 * @param serverId - Optional target server ID to scope clearance
 */
export async function clearOfflineCache(serverId?: string): Promise<void> {
  const keys = [
    scopedCacheKey(OFFLINE_COLLECTION_CACHE_KEY, serverId),
    scopedCacheKey(OFFLINE_WISHLIST_CACHE_KEY, serverId),
    scopedCacheKey(OFFLINE_PROFILE_CACHE_KEY, serverId),
    scopedCacheKey(OFFLINE_MANUAL_QUEUE_KEY, serverId),
  ];

  if (isNativeApp()) {
    try {
      for (const key of keys) {
        await Preferences.remove({ key });
      }
    } catch {
      // Ignore removal errors
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      for (const key of keys) {
        window.localStorage.removeItem(key);
      }
    } catch {
      // Ignore
    }
  }
}
