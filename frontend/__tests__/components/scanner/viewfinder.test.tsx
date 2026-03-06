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
/**
 * Tests for the Viewfinder component.
 *
 * Viewfinder is a pure presentational component with no props or hooks.
 * It renders the barcode-scanner overlay: a darkened mask, corner-bracket SVG
 * and an animated scan line.
 */
import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Viewfinder } from "@/components/scanner/viewfinder";

describe("Viewfinder", () => {
  it("renders without crashing", () => {
    const { container } = render(<Viewfinder />);
    expect(container.firstChild).not.toBeNull();
  });

  it("renders an SVG element for the corner brackets", () => {
    const { container } = render(<Viewfinder />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
  });

  it("marks the SVG as decorative (aria-hidden)", () => {
    const { container } = render(<Viewfinder />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });

  it("renders four SVG path elements for the corner brackets", () => {
    const { container } = render(<Viewfinder />);
    const paths = container.querySelectorAll("svg path");
    expect(paths).toHaveLength(4);
  });

  it("renders the scanning-line div inside the viewfinder box", () => {
    const { container } = render(<Viewfinder />);
    // The scan line bar has the distinctive bg-accent Tailwind class.
    // We cannot query by the Tailwind arbitrary-value class (brackets in selectors
    // are invalid), so we target the bg-accent helper class on the inner bar.
    const scanBar = container.querySelector(".bg-accent");
    expect(scanBar).not.toBeNull();
  });
});
