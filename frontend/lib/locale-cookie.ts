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

import { setSavedLocale } from "./capacitor/locale";

export const LOCALE_CHANGE_EVENT = "iqoqo:locale-change";

/**
 * Persists a locale preference with secure cookie attributes and notifies client providers.
 *
 * @param locale - The selected locale identifier ("en" | "pl").
 */
export function setLocaleCookie(locale: string): void {
  if (typeof document !== "undefined") {
    document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=31536000; Secure; SameSite=Lax`;
  }
  if (locale === "en" || locale === "pl") {
    setSavedLocale(locale).catch(() => {});
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(LOCALE_CHANGE_EVENT, { detail: { locale } }));
  }
}
