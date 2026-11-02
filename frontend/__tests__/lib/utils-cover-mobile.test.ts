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

import { describe, expect, it, vi, beforeEach } from "vitest";
import * as platform from "@/lib/capacitor/platform";
import * as storage from "@/lib/capacitor/storage";
import { getCoverUrl, resolveApiUrl } from "@/lib/utils";

describe("Native Mobile Cover URL Resolution", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("resolves relative cover URLs to the remote instance URL when isNativeApp is true", () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    vi.spyOn(storage, "getSyncInstanceUrl").mockReturnValue("https://preview.iqoqo.cc");

    const resolved = getCoverUrl("/api/static/covers/book123.jpg");
    expect(resolved).toBe("https://preview.iqoqo.cc/api/static/covers/book123.jpg");

    const resolvedWithTimestamp = getCoverUrl("/api/static/covers/book123.jpg", 1700000000);
    expect(resolvedWithTimestamp).toBe("https://preview.iqoqo.cc/api/static/covers/book123.jpg?t=1700000000");
  });

  it("resolves /static/covers to /api/static/covers with instance URL prefix on native mobile", () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    vi.spyOn(storage, "getSyncInstanceUrl").mockReturnValue("https://preview.iqoqo.cc");

    const resolved = resolveApiUrl("/static/covers/album.jpg");
    expect(resolved).toBe("https://preview.iqoqo.cc/api/static/covers/album.jpg");
  });

  it("leaves cover URLs relative when running in standard web browser", () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(false);

    const resolved = getCoverUrl("/api/static/covers/book123.jpg");
    expect(resolved).toBe("/api/static/covers/book123.jpg");
  });

  it("accepts absolute URLs matching the remote instance URL on native mobile", () => {
    vi.spyOn(platform, "isNativeApp").mockReturnValue(true);
    vi.spyOn(storage, "getSyncInstanceUrl").mockReturnValue("https://preview.iqoqo.cc");

    const resolved = getCoverUrl("https://preview.iqoqo.cc/api/static/covers/book123.jpg");
    expect(resolved).toBe("https://preview.iqoqo.cc/api/static/covers/book123.jpg");
  });
});
