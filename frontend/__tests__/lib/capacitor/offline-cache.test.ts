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
import * as platform from "@/lib/capacitor/platform";
import {
  saveCollectionSnapshot,
  getCachedCollectionSnapshot,
  saveWishlistSnapshot,
  getCachedWishlistSnapshot,
  saveProfileSnapshot,
  getCachedProfileSnapshot,
  enqueueOfflineManualEntry,
  getOfflineManualQueue,
  flushOfflineManualQueue,
  findOfflineDuplicate,
  clearOfflineCache,
  OFFLINE_COLLECTION_CACHE_KEY,
} from "@/lib/capacitor/offline-cache";
import { removeAuthToken, clearAllMobileStorage } from "@/lib/capacitor/storage";
import type { Item, WishlistItem, UserProfile } from "@/types/frbr";

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

describe("offline-cache", () => {
  const mockItems: Item[] = [
    {
      id: 1,
      manifestation_id: 101,
      owner_id: "user-1",
      status: "completed",
      collection_status: "own",
      title: "The Hobbit",
      isbn: "978-0-261-10221-7",
      local_barcode: "9780261102217",
      authors: ["J.R.R. Tolkien"],
      meta: {},
    } as unknown as Item,
  ];

  const mockWishlist: WishlistItem[] = [
    {
      id: 10,
      work_id: 202,
      expression_id: null,
      manifestation_id: 303,
      owner_id: "user-1",
      status: "want_to_read",
      collection_status: "wish_list",
      is_hidden: false,
      title: "Dune",
      authors: ["Frank Herbert"],
      isbn: "9780441172719",
      publisher: null,
      cover_url: null,
      cover_status: null,
      content_type: null,
      work_type: null,
      medium_type: null,
      is_owner: true,
      tags: [],
      added_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    } as WishlistItem,
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.spyOn(platform, "isNativeApp").mockReturnValue(false);
  });

  it("persists and retrieves collection snapshot in web localStorage", async () => {
    await saveCollectionSnapshot(mockItems);

    const snapshot = await getCachedCollectionSnapshot();
    expect(snapshot).not.toBeNull();
    expect(snapshot?.items).toHaveLength(1);
    expect(snapshot?.items[0].title).toBe("The Hobbit");
    expect(snapshot?.timestamp).toBeGreaterThan(0);
  });

  it("persists and retrieves wishlist snapshot in web localStorage", async () => {
    await saveWishlistSnapshot(mockWishlist);

    const snapshot = await getCachedWishlistSnapshot();
    expect(snapshot).not.toBeNull();
    expect(snapshot?.items).toHaveLength(1);
    expect(snapshot?.items[0].title).toBe("Dune");
  });

  it("uses Capacitor Preferences when on native app", async () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);

    const dummyJson = JSON.stringify({
      timestamp: 123456789,
      items: mockItems,
    });
    vi.mocked(Preferences.get).mockResolvedValueOnce({ value: dummyJson });

    const snapshot = await getCachedCollectionSnapshot();
    expect(Preferences.get).toHaveBeenCalledWith({ key: OFFLINE_COLLECTION_CACHE_KEY });
    expect(snapshot?.items[0].id).toBe(1);

    await saveCollectionSnapshot(mockItems);
    expect(Preferences.set).toHaveBeenCalledWith({
      key: OFFLINE_COLLECTION_CACHE_KEY,
      value: expect.any(String),
    });
  });

  it("finds duplicate items offline by barcode, isbn, or title", async () => {
    await saveCollectionSnapshot(mockItems);
    await saveWishlistSnapshot(mockWishlist);

    // Exact ISBN match with hyphens stripped
    const match1 = await findOfflineDuplicate("9780261102217");
    expect(match1).not.toBeNull();
    expect(match1?.matchType).toBe("collection");

    // Title match
    const match2 = await findOfflineDuplicate("Hobbit");
    expect(match2).not.toBeNull();
    expect(match2?.matchType).toBe("collection");

    // Wishlist match
    const match3 = await findOfflineDuplicate("978-0441172719");
    expect(match3).not.toBeNull();
    expect(match3?.matchType).toBe("wishlist");

    // No match
    const match4 = await findOfflineDuplicate("NonExistentItem9999");
    expect(match4).toBeNull();
  });

  it("purges offline snapshot on clearOfflineCache", async () => {
    await saveCollectionSnapshot(mockItems);
    await saveWishlistSnapshot(mockWishlist);

    await clearOfflineCache();

    expect(await getCachedCollectionSnapshot()).toBeNull();
    expect(await getCachedWishlistSnapshot()).toBeNull();
  });

  it("purges offline snapshot automatically when removeAuthToken or clearAllMobileStorage runs", async () => {
    await saveCollectionSnapshot(mockItems);
    await saveWishlistSnapshot(mockWishlist);

    await removeAuthToken();
    expect(await getCachedCollectionSnapshot()).toBeNull();

    await saveCollectionSnapshot(mockItems);
    await clearAllMobileStorage();
    expect(await getCachedCollectionSnapshot()).toBeNull();
  });

  it("persists and retrieves user profile snapshot offline", async () => {
    const mockProfile: UserProfile = {
      id: "user-42",
      email: "collector@example.com",
      display_name: "Archive Keeper",
      roles: ["user"],
      permissions: ["read:items"],
    };

    await saveProfileSnapshot(mockProfile);
    const cached = await getCachedProfileSnapshot();
    expect(cached).not.toBeNull();
    expect(cached?.email).toBe("collector@example.com");
    expect(cached?.display_name).toBe("Archive Keeper");

    await clearOfflineCache();
    expect(await getCachedProfileSnapshot()).toBeNull();
  });

  it("queues and flushes manual entries when offline", async () => {
    const entryPayload = {
      Title: "Rare Flea Market Find",
      Authors: ["Anonymous"],
      Format: "book",
      ISBN: "9781234567890",
    };

    const enqueued = await enqueueOfflineManualEntry(entryPayload);
    expect(enqueued.id).toMatch(/^offline-/);

    const queue = await getOfflineManualQueue();
    expect(queue.length).toBe(1);
    expect(queue[0].payload.Title).toBe("Rare Flea Market Find");

    // Check that optimistic item was added to collection snapshot
    const snapshot = await getCachedCollectionSnapshot();
    expect(snapshot?.items.some(i => i.title === "Rare Flea Market Find")).toBe(true);

    // Flush queue successfully
    const mockSubmit = vi.fn().mockResolvedValue({ success: true });
    const result = await flushOfflineManualQueue(mockSubmit);
    expect(result.synced).toBe(1);
    expect(result.failed).toBe(0);
    expect(mockSubmit).toHaveBeenCalledWith(entryPayload);

    // Queue is empty after flush
    const remainingQueue = await getOfflineManualQueue();
    expect(remainingQueue.length).toBe(0);

    // Provisional item was pruned from collection snapshot
    const postFlushSnapshot = await getCachedCollectionSnapshot();
    expect(postFlushSnapshot?.items.some(i => i.id === -enqueued.timestamp)).toBe(false);
  });

  it("serializes concurrent flushOfflineManualQueue calls with in-flight mutex", async () => {
    const entryPayload = {
      Title: "Unique Manual Entry",
      Authors: ["Tester"],
      Format: "book",
    };
    await enqueueOfflineManualEntry(entryPayload);

    let resolveSubmission!: (val: unknown) => void;
    const submissionPromise = new Promise(resolve => {
      resolveSubmission = resolve;
    });
    const slowSubmit = vi.fn().mockImplementation(() => submissionPromise);

    // Fire two flushes concurrently
    const flushPromise1 = flushOfflineManualQueue(slowSubmit);
    const flushPromise2 = flushOfflineManualQueue(slowSubmit);

    // Mutex should return the exact same in-flight promise
    expect(flushPromise1).toBe(flushPromise2);

    resolveSubmission({ success: true });
    const [res1, res2] = await Promise.all([flushPromise1, flushPromise2]);

    expect(res1.synced).toBe(1);
    expect(res2.synced).toBe(1);
    expect(slowSubmit).toHaveBeenCalledTimes(1);
  });
});
