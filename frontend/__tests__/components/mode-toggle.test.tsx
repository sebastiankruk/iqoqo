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

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ModeToggle } from "@/components/mode-toggle";
import { useTheme } from "next-themes";

const mockSetTheme = vi.fn();

vi.mock("next-themes", () => ({
  useTheme: vi.fn(),
}));

describe("ModeToggle Component", () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useTheme).mockReturnValue({
      theme: "light",
      setTheme: mockSetTheme,
      themes: ["light", "dark", "system"],
      systemTheme: "light",
      resolvedTheme: "light",
    });
  });

  it("renders toggle button with accessible label", () => {
    render(<ModeToggle />);

    const button = screen.getByRole("button", { name: /toggle theme/i });
    expect(button).toBeInTheDocument();
  });

  it("renders dropdown menu items when clicked and changes theme", async () => {
    render(<ModeToggle />);

    const trigger = screen.getByRole("button", { name: /toggle theme/i });
    await user.click(trigger);

    const menu = await screen.findByRole("menu");
    expect(menu).toBeInTheDocument();

    const darkOption = within(menu).getByText("Dark");
    await user.click(darkOption);
    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });

  it("allows selecting system and light themes", async () => {
    render(<ModeToggle />);

    const trigger = screen.getByRole("button", { name: /toggle theme/i });
    await user.click(trigger);

    const menu = await screen.findByRole("menu");
    const systemOption = within(menu).getByText("System");
    await user.click(systemOption);
    expect(mockSetTheme).toHaveBeenCalledWith("system");
  });
});
