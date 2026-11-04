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

import { describe, expect, it, vi } from "vitest";
import { setLocaleCookie, LOCALE_CHANGE_EVENT } from "@/lib/locale-cookie";
import * as capacitorLocale from "@/lib/capacitor/locale";

describe("setLocaleCookie", () => {
  it("sets the locale cookie with Secure and SameSite=Lax", () => {
    const cookieSetter = vi.spyOn(document, "cookie", "set");

    setLocaleCookie("pl");

    expect(cookieSetter).toHaveBeenCalledWith("NEXT_LOCALE=pl; path=/; max-age=31536000; Secure; SameSite=Lax");
  });

  it("persists locale to storage and dispatches LOCALE_CHANGE_EVENT", () => {
    const spySetSaved = vi.spyOn(capacitorLocale, "setSavedLocale").mockResolvedValue();
    const eventHandler = vi.fn();
    window.addEventListener(LOCALE_CHANGE_EVENT, eventHandler);

    setLocaleCookie("pl");

    expect(spySetSaved).toHaveBeenCalledWith("pl");
    expect(eventHandler).toHaveBeenCalled();
    const event = eventHandler.mock.calls[0][0] as CustomEvent;
    expect(event.detail).toEqual({ locale: "pl" });

    window.removeEventListener(LOCALE_CHANGE_EVENT, eventHandler);
  });
});
