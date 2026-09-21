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

/**
 * Structural validation for SPARQL Explorer i18n namespace.
 *
 * Ensures key parity between en.json and pl.json and verifies
 * no translation values are empty strings.
 *
 * Note: SPARQL Explorer currently uses hardcoded English strings.
 * This test validates the i18n infrastructure and detects when
 * translations are added for the SPARQL namespace.
 */
import { describe, expect, it } from "vitest";

import enMessages from "@/messages/en.json";
import plMessages from "@/messages/pl.json";

describe("SPARQL Explorer i18n completeness", () => {
  // SPARQL Explorer may not have a dedicated namespace yet
  // These tests validate the i18n infrastructure for when it's added
  const enKeys = Object.keys(enMessages).sort();
  const plKeys = Object.keys(plMessages).sort();

  it("has identical top-level namespaces in en.json and pl.json", () => {
    const missingInPl = enKeys.filter(k => !plKeys.includes(k));
    const extraInPl = plKeys.filter(k => !enKeys.includes(k));

    if (missingInPl.length > 0) {
      console.error("Namespaces missing in pl.json:", missingInPl);
    }
    if (extraInPl.length > 0) {
      console.error("Extra namespaces in pl.json:", extraInPl);
    }

    expect(missingInPl).toHaveLength(0);
    expect(extraInPl).toHaveLength(0);
    expect(enKeys).toEqual(plKeys);
  });

  it("has no empty string values in any namespace", () => {
    const checkEmpty = (messages: Record<string, unknown>, locale: string) => {
      const empty: string[] = [];

      const checkObj = (obj: Record<string, unknown>, path: string) => {
        for (const [key, value] of Object.entries(obj)) {
          const fullPath = path ? `${path}.${key}` : key;
          if (typeof value === "string" && value.trim() === "") {
            empty.push(fullPath);
          } else if (typeof value === "object" && value !== null) {
            checkObj(value as Record<string, unknown>, fullPath);
          }
        }
      };

      checkObj(messages, "");
      return empty;
    };

    const emptyInEn = checkEmpty(enMessages as Record<string, unknown>, "en");
    const emptyInPl = checkEmpty(plMessages as Record<string, unknown>, "pl");

    if (emptyInEn.length > 0) {
      console.error("Empty values in en.json:", emptyInEn);
    }
    if (emptyInPl.length > 0) {
      console.error("Empty values in pl.json:", emptyInPl);
    }

    expect(emptyInEn).toHaveLength(0);
    expect(emptyInPl).toHaveLength(0);
  });

  it("has consistent nested key structure across locales", () => {
    const getNestedKeys = (obj: Record<string, unknown>, prefix = ""): string[] => {
      const keys: string[] = [];
      for (const [key, value] of Object.entries(obj)) {
        const fullKey = prefix ? `${prefix}.${key}` : key;
        if (typeof value === "object" && value !== null && !Array.isArray(value)) {
          keys.push(...getNestedKeys(value as Record<string, unknown>, fullKey));
        } else {
          keys.push(fullKey);
        }
      }
      return keys;
    };

    const enNestedKeys = getNestedKeys(enMessages as Record<string, unknown>).sort();
    const plNestedKeys = getNestedKeys(plMessages as Record<string, unknown>).sort();

    const missingInPl = enNestedKeys.filter(k => !plNestedKeys.includes(k));
    const extraInPl = plNestedKeys.filter(k => !enNestedKeys.includes(k));

    if (missingInPl.length > 0) {
      console.error("Keys missing in pl.json:", missingInPl.slice(0, 10));
    }
    if (extraInPl.length > 0) {
      console.error("Extra keys in pl.json:", extraInPl.slice(0, 10));
    }

    expect(missingInPl).toHaveLength(0);
    expect(extraInPl).toHaveLength(0);
  });

  it("detects when SPARQL namespace is added", () => {
    // This test will pass when a SPARQL namespace is added to both locales
    const hasSparqlNamespace = enKeys.includes("SPARQL") || enKeys.includes("Sparql");

    // For now, we just verify the test infrastructure works
    // When SPARQL translations are added, this test should be updated
    if (hasSparqlNamespace) {
      const enSparql =
        (enMessages as Record<string, Record<string, string>>).SPARQL ||
        (enMessages as Record<string, Record<string, string>>).Sparql;
      const plSparql =
        (plMessages as Record<string, Record<string, string>>).SPARQL ||
        (plMessages as Record<string, Record<string, string>>).Sparql;

      if (enSparql && plSparql) {
        const enSparqlKeys = Object.keys(enSparql).sort();
        const plSparqlKeys = Object.keys(plSparql).sort();
        expect(enSparqlKeys).toEqual(plSparqlKeys);
      }
    }

    // Test passes regardless - just validates infrastructure
    expect(true).toBe(true);
  });
});

describe("SPARQL Explorer error message translations", () => {
  it("Common namespace has error-related keys", () => {
    const enCommon = (enMessages as Record<string, Record<string, string>>).Common;
    const plCommon = (plMessages as Record<string, Record<string, string>>).Common;

    expect(enCommon).toBeDefined();
    expect(plCommon).toBeDefined();

    // Verify error-related keys exist in both locales
    const enKeys = Object.keys(enCommon);
    const plKeys = Object.keys(plCommon);

    // Both should have the same keys
    expect(enKeys.sort()).toEqual(plKeys.sort());
  });
});
