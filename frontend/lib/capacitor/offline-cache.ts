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
export async function saveProfileSnapshot(profile: UserProfile): Promise<void> {
  const payload: OfflineProfileSnapshot = {
    timestamp: Date.now(),
    profile,
  };
  const serialized = JSON.stringify(payload);

  if (isNativeApp()) {
    try {
      await Preferences.set({ key: OFFLINE_PROFILE_CACHE_KEY, value: serialized });
    } catch {
      // Ignore preferences write failure
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(OFFLINE_PROFILE_CACHE_KEY, serialized);
    } catch {
      // Ignore localStorage quotas
    }
  }
}

/**
 * Retrieve cached user profile snapshot if available.
 *
 * @returns Cached UserProfile or null
 */
export async function getCachedProfileSnapshot(): Promise<UserProfile | null> {
  let serialized: string | null = null;

  if (isNativeApp()) {
    try {
      const res = await Preferences.get({ key: OFFLINE_PROFILE_CACHE_KEY });
      serialized = res.value;
    } catch {
      serialized = null;
    }
  }

  if (!serialized && typeof window !== "undefined" && window.localStorage) {
    try {
      serialized = window.localStorage.getItem(OFFLINE_PROFILE_CACHE_KEY);
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
export async function saveCollectionSnapshot(items: Item[]): Promise<void> {
  const payload: OfflineCollectionSnapshot = {
    timestamp: Date.now(),
    items,
  };
  const serialized = JSON.stringify(payload);

  if (isNativeApp()) {
    try {
      await Preferences.set({ key: OFFLINE_COLLECTION_CACHE_KEY, value: serialized });
    } catch {
      // Ignore preferences write failure
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(OFFLINE_COLLECTION_CACHE_KEY, serialized);
    } catch {
      // Ignore localStorage quotas / private browsing errors
    }
  }
}

/**
 * Retrieve cached collection snapshot if available.
 *
 * @returns Offline collection snapshot or null
 */
export async function getCachedCollectionSnapshot(): Promise<OfflineCollectionSnapshot | null> {
  let serialized: string | null = null;

  if (isNativeApp()) {
    try {
      const res = await Preferences.get({ key: OFFLINE_COLLECTION_CACHE_KEY });
      serialized = res.value;
    } catch {
      serialized = null;
    }
  }

  if (!serialized && typeof window !== "undefined" && window.localStorage) {
    try {
      serialized = window.localStorage.getItem(OFFLINE_COLLECTION_CACHE_KEY);
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
export async function saveWishlistSnapshot(items: WishlistItem[]): Promise<void> {
  const payload: OfflineWishlistSnapshot = {
    timestamp: Date.now(),
    items,
  };
  const serialized = JSON.stringify(payload);

  if (isNativeApp()) {
    try {
      await Preferences.set({ key: OFFLINE_WISHLIST_CACHE_KEY, value: serialized });
    } catch {
      // Ignore preferences write failure
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(OFFLINE_WISHLIST_CACHE_KEY, serialized);
    } catch {
      // Ignore localStorage quotas
    }
  }
}

/**
 * Retrieve cached wishlist snapshot if available.
 *
 * @returns Offline wishlist snapshot or null
 */
export async function getCachedWishlistSnapshot(): Promise<OfflineWishlistSnapshot | null> {
  let serialized: string | null = null;

  if (isNativeApp()) {
    try {
      const res = await Preferences.get({ key: OFFLINE_WISHLIST_CACHE_KEY });
      serialized = res.value;
    } catch {
      serialized = null;
    }
  }

  if (!serialized && typeof window !== "undefined" && window.localStorage) {
    try {
      serialized = window.localStorage.getItem(OFFLINE_WISHLIST_CACHE_KEY);
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
export async function getOfflineManualQueue(): Promise<OfflineManualEntry[]> {
  let serialized: string | null = null;

  if (isNativeApp()) {
    try {
      const res = await Preferences.get({ key: OFFLINE_MANUAL_QUEUE_KEY });
      serialized = res.value;
    } catch {
      serialized = null;
    }
  }

  if (!serialized && typeof window !== "undefined" && window.localStorage) {
    try {
      serialized = window.localStorage.getItem(OFFLINE_MANUAL_QUEUE_KEY);
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

  if (isNativeApp()) {
    try {
      await Preferences.set({ key: OFFLINE_MANUAL_QUEUE_KEY, value: serialized });
    } catch {
      // Ignore
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(OFFLINE_MANUAL_QUEUE_KEY, serialized);
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

/**
 * Flush queued offline manual entries to the backend API.
 *
 * @param submitFn - The async function that submits each payload to the server
 * @returns Counts of synced and failed items
 */
export async function flushOfflineManualQueue(
  submitFn: (payload: OfflineManualEntry["payload"]) => Promise<unknown>
): Promise<{ synced: number; failed: number }> {
  const queue = await getOfflineManualQueue();
  if (queue.length === 0) return { synced: 0, failed: 0 };

  const remaining: OfflineManualEntry[] = [];
  let synced = 0;
  let failed = 0;

  for (const entry of queue) {
    try {
      await submitFn(entry.payload);
      synced++;
    } catch (e) {
      console.warn("Failed to flush offline manual entry:", entry.id, e);
      failed++;
      remaining.push(entry);
    }
  }

  const serialized = JSON.stringify(remaining);
  if (isNativeApp()) {
    try {
      await Preferences.set({ key: OFFLINE_MANUAL_QUEUE_KEY, value: serialized });
    } catch {
      // Ignore
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(OFFLINE_MANUAL_QUEUE_KEY, serialized);
    } catch {
      // Ignore
    }
  }

  return { synced, failed };
}

/**
 * Purge all cached collection, wishlist, profile, and manual queue offline records.
 * Called on logout, server switch, or explicit cache clearance.
 */
export async function clearOfflineCache(): Promise<void> {
  if (isNativeApp()) {
    try {
      await Preferences.remove({ key: OFFLINE_COLLECTION_CACHE_KEY });
      await Preferences.remove({ key: OFFLINE_WISHLIST_CACHE_KEY });
      await Preferences.remove({ key: OFFLINE_PROFILE_CACHE_KEY });
      await Preferences.remove({ key: OFFLINE_MANUAL_QUEUE_KEY });
    } catch {
      // Ignore removal errors
    }
  }

  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.removeItem(OFFLINE_COLLECTION_CACHE_KEY);
      window.localStorage.removeItem(OFFLINE_WISHLIST_CACHE_KEY);
      window.localStorage.removeItem(OFFLINE_PROFILE_CACHE_KEY);
      window.localStorage.removeItem(OFFLINE_MANUAL_QUEUE_KEY);
    } catch {
      // Ignore
    }
  }
}
