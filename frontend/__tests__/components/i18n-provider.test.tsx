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
import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ClientI18nProvider } from "@/components/i18n-provider";
import { setLocaleCookie } from "@/lib/locale-cookie";

describe("ClientI18nProvider", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders children with initial locale", () => {
    render(
      <ClientI18nProvider initialLocale="en" initialMessages={{}}>
        <div data-testid="child-element">Hello World</div>
      </ClientI18nProvider>
    );

    expect(screen.getByTestId("child-element")).toBeInTheDocument();
  });

  it("dynamically updates document lang when locale changes via setLocaleCookie", async () => {
    render(
      <ClientI18nProvider initialLocale="en" initialMessages={{}}>
        <div data-testid="child-element">Hello World</div>
      </ClientI18nProvider>
    );

    act(() => {
      setLocaleCookie("pl");
    });

    expect(document.documentElement.lang).toBe("pl");
  });
});
