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

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { StarRating } from "@/components/social/star-rating";
import { vi, describe, it, expect } from "vitest";

describe("StarRating", () => {
  it("renders default 5 stars with correct initial filled rating", () => {
    const { container } = render(<StarRating rating={3} />);

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(5);

    const filledStars = container.querySelectorAll(".fill-amber-400");
    expect(filledStars).toHaveLength(3);
  });

  it("calls onChange when an interactive star is clicked", () => {
    const handleChange = vi.fn();
    render(<StarRating rating={2} onChange={handleChange} />);

    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[3]); // 4th star (rating 4)

    expect(handleChange).toHaveBeenCalledWith(4);
  });

  it("updates filled stars preview on mouse enter and restores on mouse leave", () => {
    const { container } = render(<StarRating rating={2} />);

    const buttons = screen.getAllByRole("button");
    fireEvent.mouseEnter(buttons[4]); // 5th star

    let filledStars = container.querySelectorAll(".fill-amber-400");
    expect(filledStars).toHaveLength(5);

    // Mouse leaves root container
    fireEvent.mouseLeave(container.firstChild as Element);

    filledStars = container.querySelectorAll(".fill-amber-400");
    expect(filledStars).toHaveLength(2);
  });

  it("disables interactivity when readOnly is true", () => {
    const handleChange = vi.fn();
    const { container } = render(<StarRating rating={4} readOnly onChange={handleChange} />);

    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toBeDisabled();

    fireEvent.click(buttons[1]);
    expect(handleChange).not.toHaveBeenCalled();

    // Hover should not change filled stars in read-only mode
    fireEvent.mouseEnter(buttons[0]);
    const filledStars = container.querySelectorAll(".fill-amber-400");
    expect(filledStars).toHaveLength(4);
  });
});
