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
import { Preferences } from "@capacitor/preferences";
import { isNativeApp } from "./platform";

export const LOCALE_KEY = "iqoqo_locale";

/**
 * Detect the device's system language, falling back to English if not Polish.
 *
 * @returns {string} Supported locale ("en" | "pl").
 */
export function getDeviceLocale(): "en" | "pl" {
  if (typeof navigator !== "undefined" && navigator.languages && navigator.languages.length > 0) {
    for (const lang of navigator.languages) {
      if (lang.toLowerCase().startsWith("pl")) {
        return "pl";
      }
      if (lang.toLowerCase().startsWith("en")) {
        return "en";
      }
    }
  }
  if (typeof navigator !== "undefined" && navigator.language) {
    if (navigator.language.toLowerCase().startsWith("pl")) {
      return "pl";
    }
  }
  return "en";
}

/**
 * Retrieve the user's preferred saved locale.
 *
 * @returns {Promise<string>} Supported locale ("en" | "pl").
 */
export async function getSavedLocale(): Promise<"en" | "pl"> {
  if (isNativeApp()) {
    const { value } = await Preferences.get({ key: LOCALE_KEY });
    if (value === "pl" || value === "en") {
      return value;
    }
  } else if (typeof window !== "undefined") {
    const val = window.localStorage.getItem(LOCALE_KEY);
    if (val === "pl" || val === "en") {
      return val;
    }
  }
  return getDeviceLocale();
}

/**
 * Save the user's preferred locale.
 *
 * @param {"en" | "pl"} locale - Chosen locale
 * @returns {Promise<void>}
 */
export async function setSavedLocale(locale: "en" | "pl"): Promise<void> {
  if (isNativeApp()) {
    await Preferences.set({ key: LOCALE_KEY, value: locale });
  } else if (typeof window !== "undefined") {
    window.localStorage.setItem(LOCALE_KEY, locale);
  }
}
