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
    const emptyInEn = Object.entries(enHelpRequests).filter(([_k, v]) => v === "");
    const emptyInPl = Object.entries(plHelpRequests).filter(([_k, v]) => v === "");

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
