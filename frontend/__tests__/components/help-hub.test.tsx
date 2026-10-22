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
import HelpHubPage from "@/app/help/page";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
  useLocale: () => "en",
}));

vi.mock("@/components/dashboard/navbar", () => ({
  Navbar: () => <nav data-testid="navbar">Navbar</nav>,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer">Footer</footer>,
}));

describe("HelpHubPage", () => {
  it("renders help articles and categories", () => {
    render(<HelpHubPage />);

    expect(screen.getByTestId("navbar")).toBeInTheDocument();
    expect(screen.getByTestId("footer")).toBeInTheDocument();
    expect(screen.getByText("Beyond the Bookshelf: How iqoqo Organizes Your World")).toBeInTheDocument();
    expect(screen.getByText("From Camera to Catalog: Scanning, Manual Entry & Curatorial Help")).toBeInTheDocument();
    expect(screen.getByText("The iqoqo Federation: Connected Libraries, Sovereign Data")).toBeInTheDocument();
  });
});
