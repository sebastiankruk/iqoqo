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
 * Structural validation for Federation i18n namespaces (FederationConsent, AdminFederation).
 *
 * Ensures key parity between en.json and pl.json and verifies
 * no translation values are empty strings.
 */
import { describe, expect, it } from "vitest";

import enMessages from "@/messages/en.json";
import plMessages from "@/messages/pl.json";

describe("Federation i18n namespaces key parity", () => {
  const namespaces = ["FederationConsent", "AdminFederation"] as const;

  for (const ns of namespaces) {
    describe(`Namespace ${ns}`, () => {
      const enNs = (enMessages as unknown as Record<string, Record<string, string>>)[ns];
      const plNs = (plMessages as unknown as Record<string, Record<string, string>>)[ns];

      it(`exists in both en.json and pl.json`, () => {
        expect(enNs).toBeDefined();
        expect(plNs).toBeDefined();
      });

      it(`has identical keys in en.json and pl.json for ${ns}`, () => {
        const enKeys = Object.keys(enNs || {}).sort();
        const plKeys = Object.keys(plNs || {}).sort();

        const missingInPl = enKeys.filter(k => !plKeys.includes(k));
        const extraInPl = plKeys.filter(k => !enKeys.includes(k));

        expect(missingInPl).toHaveLength(0);
        expect(extraInPl).toHaveLength(0);
        expect(enKeys).toEqual(plKeys);
      });

      it(`has no empty string values in either locale for ${ns}`, () => {
        const emptyInEn = Object.entries(enNs || {}).filter(([, v]) => v === "");
        const emptyInPl = Object.entries(plNs || {}).filter(([, v]) => v === "");

        expect(emptyInEn).toHaveLength(0);
        expect(emptyInPl).toHaveLength(0);
      });
    });
  }
});
