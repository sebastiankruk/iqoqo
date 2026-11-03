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

import { afterEach, describe, expect, it, vi } from "vitest";
import { getCoverTimestamp, resolveApiUrl, getPublicBaseUrl, resolvePublicUrl } from "@/lib/utils";
import * as storage from "@/lib/capacitor/storage";
import * as platform from "@/lib/capacitor/platform";

describe("getCoverTimestamp", () => {
  it("returns empty string for invalid timestamps", () => {
    expect(getCoverTimestamp({ cover_status_updated_at: "not-a-date" })).toBe("");
  });

  it("returns a parsed timestamp", () => {
    expect(getCoverTimestamp({ cover_status_updated_at: "2026-01-01T00:00:00.000Z" })).toBe(
      Date.parse("2026-01-01T00:00:00.000Z")
    );
  });
});

describe("resolveApiUrl", () => {
  const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

  afterEach(() => {
    if (originalApiUrl === undefined) delete process.env.NEXT_PUBLIC_API_URL;
    else process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  });

  it("resolves local relative paths", () => {
    expect(resolveApiUrl("/items")).toBe("/api/items");
  });

  it("allows absolute URLs only for an explicitly configured host", () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test/api";
    expect(resolveApiUrl("https://api.example.test/covers/1.jpg")).toBe("https://api.example.test/covers/1.jpg");
    expect(resolveApiUrl("https://untrusted.example/covers/1.jpg")).toBe("/api");
    expect(resolveApiUrl("https://api.example.test:8443/covers/1.jpg")).toBe("/api");
    expect(resolveApiUrl("https://user:secret@api.example.test/covers/1.jpg")).toBe("/api");
  });

  it("rejects absolute URLs that downgrade the configured scheme", () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.example.test/api";
    expect(resolveApiUrl("http://api.example.test/covers/1.jpg")).toBe("/api");
  });

  it("rejects unsupported URL protocols", () => {
    expect(resolveApiUrl("javascript:alert(1)")).toBe("/api");
  });
});

describe("getPublicBaseUrl and resolvePublicUrl", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("resolves to instance URL when running on native app", () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    vi.spyOn(storage, "getSyncInstanceUrl").mockReturnValue("https://preview.iqoqo.cc");

    expect(getPublicBaseUrl()).toBe("https://preview.iqoqo.cc");
    expect(resolvePublicUrl("/share/my-token")).toBe("https://preview.iqoqo.cc/share/my-token");
    expect(resolvePublicUrl("https://other.com/link")).toBe("https://other.com/link");
  });

  it("resolves to instance URL on localhost or capacitor origin if instance URL exists", () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(false);
    vi.spyOn(storage, "getSyncInstanceUrl").mockReturnValue("https://my-instance.iqoqo.app");

    // In JSDOM, window.location.hostname is localhost
    expect(getPublicBaseUrl()).toBe("https://my-instance.iqoqo.app");
    expect(resolvePublicUrl("/api/public/feed.xml")).toBe("https://my-instance.iqoqo.app/api/public/feed.xml");
  });
});
