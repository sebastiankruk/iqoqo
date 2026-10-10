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
import * as fs from "node:fs";
import * as path from "node:path";

describe("Sidebar Architectural Constraints (Task 4.2 Non-Goals)", () => {
  const sidebarDir = path.resolve(__dirname, "../../../../components/item/sidebar");
  const extractedComponents = [
    "sidebar-cover.tsx",
    "sidebar-status-badges.tsx",
    "sidebar-lending-info.tsx",
    "sidebar-identifiers.tsx",
    "sidebar-actions.tsx",
    "sidebar-frbr-info.tsx",
  ];

  it("ensures no extracted presentational component imports useItemSidebarActions", () => {
    for (const filename of extractedComponents) {
      const filePath = path.join(sidebarDir, filename);
      const content = fs.readFileSync(filePath, "utf-8");
      expect(
        content.includes("useItemSidebarActions"),
        `${filename} must not import useItemSidebarActions (regions take props, not the hook)`
      ).toBe(false);
    }
  });

  it("ensures no extracted presentational component defines or opens a context provider", () => {
    for (const filename of extractedComponents) {
      const filePath = path.join(sidebarDir, filename);
      const content = fs.readFileSync(filePath, "utf-8");
      expect(content.includes("createContext"), `${filename} must not create a React Context`).toBe(false);
      expect(content.includes(".Provider"), `${filename} must not open a React Context Provider`).toBe(false);
    }
  });
});
