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
 * Viewfinder renders the barcode-scanner overlay: a darkened mask, corner-bracket SVG
 * and an animated scan line, and handles the BarcodeDetector API loop.
 */
import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll } from "vitest"; // <-- Added vi and beforeAll
import { Viewfinder } from "@/components/scanner/viewfinder";

describe("Viewfinder", () => {
  const mockOnDetect = vi.fn(); // Create a reusable mock function for the required prop

  // Mock the camera API so the component doesn't crash in JSDOM
  beforeAll(() => {
    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: vi.fn() }] // Mock the stream and track stopping
        }),
      },
      writable: true,
    });
  });

  it("renders without crashing", () => {
    const { container } = render(<Viewfinder onDetect={mockOnDetect} />); // <-- Added prop
    expect(container.firstChild).not.toBeNull();
  });

  it("renders an SVG element for the corner brackets", () => {
    const { container } = render(<Viewfinder onDetect={mockOnDetect} />); // <-- Added prop
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
  });

  it("marks the SVG as decorative (aria-hidden)", () => {
    const { container } = render(<Viewfinder onDetect={mockOnDetect} />); // <-- Added prop
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("aria-hidden", "true"); // Make sure this is added in your component!
  });

  it("renders four SVG path elements for the corner brackets", () => {
    const { container } = render(<Viewfinder onDetect={mockOnDetect} />); // <-- Added prop
    const paths = container.querySelectorAll("svg path");
    expect(paths).toHaveLength(4);
  });

  it("renders the scanning-line div inside the viewfinder box", () => {
    const { container } = render(<Viewfinder onDetect={mockOnDetect} />); // <-- Added prop
    const scanBar = container.querySelector(".bg-accent");
    expect(scanBar).not.toBeNull();
  });
});
