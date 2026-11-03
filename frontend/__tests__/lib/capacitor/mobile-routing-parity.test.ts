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
import { describe, it, expect } from "vitest";
import { PLACEHOLDER_PARAM, extractParamFromPathname } from "@/lib/capacitor/route-params";

describe("mobile routing parity contract", () => {
  it("enforces canonical placeholder slug value", () => {
    expect(PLACEHOLDER_PARAM).toBe("_placeholder");
  });

  const supportedDynamicRoutes = [
    { entity: "item", param: "id", sampleValue: "101", path: "/item/101" },
    { entity: "manifestation", param: "id", sampleValue: "202", path: "/manifestation/202" },
    { entity: "work", param: "id", sampleValue: "303", path: "/work/303" },
    { entity: "expression", param: "id", sampleValue: "404", path: "/expression/404" },
    { entity: "u", param: "username", sampleValue: "curator_bob", path: "/u/curator_bob" },
    { entity: "share", param: "slug", sampleValue: "shared_shelf_token", path: "/share/shared_shelf_token" },
    { entity: "help", param: "slug", sampleValue: "curators-handbook", path: "/help/curators-handbook" },
  ];

  it.each(supportedDynamicRoutes)(
    "extracts dynamic parameter for $entity from native webview path",
    ({ param, sampleValue, path }) => {
      expect(extractParamFromPathname(path, param)).toBe(sampleValue);
    }
  );

  it.each(supportedDynamicRoutes)(
    "filters out placeholder slug from native webview path for $entity",
    ({ entity, param }) => {
      const placeholderPath = `/${entity}/${PLACEHOLDER_PARAM}`;
      expect(extractParamFromPathname(placeholderPath, param)).toBeUndefined();
    }
  );
});
