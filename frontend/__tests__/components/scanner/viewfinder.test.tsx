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
