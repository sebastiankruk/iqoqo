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

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CookieConsent } from "@/components/cookie-consent";

describe("CookieConsent Component", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders banner when consent has not been given", () => {
    render(<CookieConsent />);

    expect(screen.getByText(/Small crumbs of data/i)).toBeInTheDocument();
    expect(screen.getByText(/Privacy Policy/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Got it/i })).toBeInTheDocument();
  });

  it("does not render when consent is already recorded in localStorage", () => {
    localStorage.setItem("iqoqo-cookie-consent", "true");
    render(<CookieConsent />);

    expect(screen.queryByText(/Small crumbs of data/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Got it/i })).not.toBeInTheDocument();
  });

  it("saves consent to localStorage and dismisses banner upon clicking 'Got it'", () => {
    render(<CookieConsent />);

    const button = screen.getByRole("button", { name: /Got it/i });
    expect(button).toBeInTheDocument();

    fireEvent.click(button);

    expect(localStorage.getItem("iqoqo-cookie-consent")).toBe("true");
    expect(screen.queryByText(/Small crumbs of data/i)).not.toBeInTheDocument();
  });
});
