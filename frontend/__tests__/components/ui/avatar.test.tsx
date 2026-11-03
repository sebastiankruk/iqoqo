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
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Avatar } from "@/components/ui/avatar";

describe("Avatar component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders fallback initials when src is not provided", () => {
    render(<Avatar fallback="JD" alt="John Doe" />);
    expect(screen.getByText("JD")).toBeInTheDocument();
  });

  it("renders fallback question mark when neither src nor fallback provided", () => {
    render(<Avatar alt="Unknown User" />);
    expect(screen.getByText("?")).toBeInTheDocument();
  });

  it("renders image with referrerPolicy='no-referrer' when src is provided", () => {
    render(<Avatar src="https://lh3.googleusercontent.com/a/avatar123" alt="Google Avatar" fallback="G" />);
    const img = screen.getByAltText("Google Avatar");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://lh3.googleusercontent.com/a/avatar123");
    expect(img).toHaveAttribute("referrerPolicy", "no-referrer");
  });

  it("falls back to initials when image triggers onError", () => {
    const { container } = render(
      <Avatar src="https://example.com/broken-avatar.png" alt="Broken Avatar" fallback="BA" />
    );
    const img = screen.getByAltText("Broken Avatar");
    expect(img).toBeInTheDocument();

    fireEvent.error(img);

    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("BA")).toBeInTheDocument();
  });
});
