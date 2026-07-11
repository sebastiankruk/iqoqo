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

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { LanguageToggle } from "@/components/language-toggle";

const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: mockRefresh,
  }),
}));

let currentLocale = "en";
vi.mock("next-intl", () => ({
  useLocale: () => currentLocale,
}));

describe("LanguageToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentLocale = "en";
    document.cookie = "";
  });

  it("renders the language toggle button", () => {
    render(<LanguageToggle />);
    expect(screen.getByRole("button", { name: /toggle language/i })).toBeInTheDocument();
  });

  it("shows checkmark next to English when locale is en", async () => {
    currentLocale = "en";
    render(<LanguageToggle />);

    const trigger = screen.getByRole("button", { name: /toggle language/i });
    await userEvent.click(trigger);

    expect(screen.getByText("English")).toBeInTheDocument();
    expect(screen.getByText("Polski")).toBeInTheDocument();
  });

  it("updates cookie and refreshes router on selection", async () => {
    render(<LanguageToggle />);

    const trigger = screen.getByRole("button", { name: /toggle language/i });
    await userEvent.click(trigger);

    const polishItem = screen.getByText("Polski");
    await userEvent.click(polishItem);

    expect(document.cookie).toContain("NEXT_LOCALE=pl");
    expect(mockRefresh).toHaveBeenCalled();
  });
});
