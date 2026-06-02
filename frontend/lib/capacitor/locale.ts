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

const LOCALE_KEY = "iqoqo_locale";

/**
 * Return the active UI locale.
 * - Native: reads from Capacitor Preferences.
 * - Web: reads from the NEXT_LOCALE cookie set by next-intl.
 *
 * @returns {Promise<string>} The BCP-47 locale tag (e.g. "en", "pl").
 */
export async function getStoredLocale(): Promise<string> {
  if (!isNativeApp()) {
    return (
      document.cookie
        .split("; ")
        .find(c => c.startsWith("NEXT_LOCALE="))
        ?.split("=")[1] ?? "en"
    );
  }
  const { value } = await Preferences.get({ key: LOCALE_KEY });
  return value ?? "en";
}

/**
 * Persist the active UI locale.
 * - Native: stores in Capacitor Preferences.
 * - Web: writes the NEXT_LOCALE cookie consumed by next-intl.
 *
 * @param locale - BCP-47 locale tag (e.g. "en", "pl").
 */
export async function setStoredLocale(locale: string): Promise<void> {
  if (isNativeApp()) {
    await Preferences.set({ key: LOCALE_KEY, value: locale });
  } else {
    document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=${60 * 60 * 24 * 365}`;
  }
}
