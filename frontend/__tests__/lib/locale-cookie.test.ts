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
import { setLocaleCookie } from "@/lib/locale-cookie";

describe("setLocaleCookie", () => {
  it("sets the locale cookie with Secure and SameSite=Lax", () => {
    const cookieSetter = vi.spyOn(document, "cookie", "set");

    setLocaleCookie("pl");

    expect(cookieSetter).toHaveBeenCalledWith("NEXT_LOCALE=pl; path=/; max-age=31536000; Secure; SameSite=Lax");
  });
});
