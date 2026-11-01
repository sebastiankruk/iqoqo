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
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { extractParamFromPathname, useResolvedRouteParam, PLACEHOLDER_PARAM } from "@/lib/capacitor/route-params";
import * as navigation from "next/navigation";

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

describe("lib/capacitor/route-params", () => {
  describe("extractParamFromPathname", () => {
    it("extracts ID from standard /item/:id path", () => {
      expect(extractParamFromPathname("/item/123", "id")).toBe("123");
      expect(extractParamFromPathname("/manifestation/456", "id")).toBe("456");
      expect(extractParamFromPathname("/work/789", "id")).toBe("789");
    });

    it("extracts username and slug from respective paths", () => {
      expect(extractParamFromPathname("/u/alice", "username")).toBe("alice");
      expect(extractParamFromPathname("/help/getting-started", "slug")).toBe("getting-started");
    });

    it("ignores placeholder parameters", () => {
      expect(extractParamFromPathname(`/item/${PLACEHOLDER_PARAM}`, "id")).toBeUndefined();
      expect(extractParamFromPathname(`/${PLACEHOLDER_PARAM}`, "id")).toBeUndefined();
    });

    it("handles trailing slashes and empty paths", () => {
      expect(extractParamFromPathname("/item/42/", "id")).toBe("42");
      expect(extractParamFromPathname("", "id")).toBeUndefined();
      expect(extractParamFromPathname("/", "id")).toBeUndefined();
    });
  });

  describe("useResolvedRouteParam hook", () => {
    const originalLocation = window.location;

    beforeEach(() => {
      vi.resetAllMocks();
    });

    afterEach(() => {
      Object.defineProperty(window, "location", {
        writable: true,
        value: originalLocation,
      });
    });

    it("returns param directly when useParams returns a valid non-placeholder value", () => {
      vi.mocked(navigation.useParams).mockReturnValue({ id: "99" });

      const { result } = renderHook(() => useResolvedRouteParam("id"));
      expect(result.current).toBe("99");
    });

    it("resolves from window.location.pathname when useParams returns _placeholder", () => {
      vi.mocked(navigation.useParams).mockReturnValue({ id: PLACEHOLDER_PARAM });

      Object.defineProperty(window, "location", {
        writable: true,
        value: {
          pathname: "/item/314",
          search: "",
        },
      });

      const { result } = renderHook(() => useResolvedRouteParam("id"));
      expect(result.current).toBe("314");
    });

    it("falls back to search query params when pathname cannot be parsed", () => {
      vi.mocked(navigation.useParams).mockReturnValue({ id: PLACEHOLDER_PARAM });

      Object.defineProperty(window, "location", {
        writable: true,
        value: {
          pathname: `/item/${PLACEHOLDER_PARAM}`,
          search: "?id=555",
        },
      });

      const { result } = renderHook(() => useResolvedRouteParam("id"));
      expect(result.current).toBe("555");
    });
  });
});
