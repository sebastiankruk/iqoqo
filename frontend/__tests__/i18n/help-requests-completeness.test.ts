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

/**
 * Structural validation for HelpRequests i18n namespace.
 *
 * Ensures key parity between en.json and pl.json and verifies
 * no translation values are empty strings.
 */
import { describe, expect, it } from "vitest";

import enMessages from "@/messages/en.json";
import plMessages from "@/messages/pl.json";

describe("HelpRequests i18n namespace", () => {
  const enHelpRequests = enMessages.HelpRequests as Record<string, string>;
  const plHelpRequests = plMessages.HelpRequests as Record<string, string>;

  it("has identical keys in en.json and pl.json", () => {
    const enKeys = Object.keys(enHelpRequests).sort();
    const plKeys = Object.keys(plHelpRequests).sort();

    // Keys missing in pl.json that exist in en.json
    const missingInPl = enKeys.filter(k => !plKeys.includes(k));
    // Keys in pl.json that don't exist in en.json
    const extraInPl = plKeys.filter(k => !enKeys.includes(k));

    if (missingInPl.length > 0) {
      console.error("Keys missing in pl.json:", missingInPl);
    }
    if (extraInPl.length > 0) {
      console.error("Extra keys in pl.json:", extraInPl);
    }

    expect(missingInPl).toHaveLength(0);
    expect(extraInPl).toHaveLength(0);
    expect(enKeys).toEqual(plKeys);
  });

  it("has no empty string values in either locale", () => {
    const emptyInEn = Object.entries(enHelpRequests).filter(([, v]) => v === "");
    const emptyInPl = Object.entries(plHelpRequests).filter(([, v]) => v === "");

    if (emptyInEn.length > 0) {
      console.error(
        "Empty values in en.json:",
        emptyInEn.map(([k]) => k)
      );
    }
    if (emptyInPl.length > 0) {
      console.error(
        "Empty values in pl.json:",
        emptyInPl.map(([k]) => k)
      );
    }

    expect(emptyInEn).toHaveLength(0);
    expect(emptyInPl).toHaveLength(0);
  });
});
