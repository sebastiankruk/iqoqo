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
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Footer } from "@/components/dashboard/footer";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  useLocale: () => "en",
}));

describe("Footer", () => {
  it("renders help and library directory links", () => {
    render(<Footer />);

    const helpLink = screen.getByRole("link", { name: "Help" });
    expect(helpLink).toHaveAttribute("href", "/help");

    const librariesLink = screen.getByRole("link", { name: "Libraries" });
    expect(librariesLink).toHaveAttribute("href", "/federation/directory");
  });
});
