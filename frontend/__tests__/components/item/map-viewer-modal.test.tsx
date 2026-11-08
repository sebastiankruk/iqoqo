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
import { describe, it, expect, vi } from "vitest";
import { MapViewerModal, type MapAttachmentItem } from "@/components/item/map-viewer-modal";

// Mock Next.js Image component
vi.mock("next/image", () => ({
  default: ({ src, alt, ...props }: { src: string; alt: string } & Record<string, unknown>) => {
    const rest = { ...props };
    delete rest.fill;
    delete rest.priority;
    delete rest.unoptimized;
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...rest} />;
  },
}));

describe("MapViewerModal", () => {
  const sampleMaps: MapAttachmentItem[] = [
    {
      id: "map-1",
      title: "Middle-earth West",
      type: "cartographic_map",
      image_url: "/uploads/maps/middle_earth_west.jpg",
      scale: "1:1,000,000",
      projection: "Lambert Conformal",
    },
    {
      id: "map-2",
      title: "Mordor Regional Detail",
      type: "thematic_map",
      image_url: "/uploads/maps/mordor.jpg",
      scale: "1:250,000",
      projection: "Mercator",
    },
  ];

  it("renders map details, scale, projection, and image when open", () => {
    render(<MapViewerModal isOpen={true} onClose={vi.fn()} maps={sampleMaps} initialIndex={0} />);

    expect(screen.getByText("Middle-earth West")).toBeInTheDocument();
    expect(screen.getByText(/1:1,000,000/)).toBeInTheDocument();
    expect(screen.getByText(/Lambert Conformal/)).toBeInTheDocument();

    const img = screen.getByRole("img", { name: "Middle-earth West" });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", expect.stringContaining("middle_earth_west.jpg"));
  });

  it("renders fallback message when map has no image URL", () => {
    const noImageMap: MapAttachmentItem[] = [
      {
        id: "map-no-img",
        title: "Lost Map",
        type: "sketch_map",
        image_url: null,
      },
    ];

    render(<MapViewerModal isOpen={true} onClose={vi.fn()} maps={noImageMap} />);

    expect(screen.getByText("Lost Map")).toBeInTheDocument();
    expect(screen.getByText("No map image available for this supplement.")).toBeInTheDocument();
  });

  it("handles zoom in and zoom out within limits [1x, 5x]", () => {
    render(<MapViewerModal isOpen={true} onClose={vi.fn()} maps={sampleMaps} />);

    const zoomOutBtn = screen.getByLabelText("Zoom Out");
    const zoomInBtn = screen.getByLabelText("Zoom In");

    // Initially 100%, zoom out disabled
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(zoomOutBtn).toBeDisabled();

    // Zoom in once -> 150%
    fireEvent.click(zoomInBtn);
    expect(screen.getByText("150%")).toBeInTheDocument();
    expect(zoomOutBtn).not.toBeDisabled();

    // Zoom in repeatedly up to 500% (5x)
    for (let i = 0; i < 7; i++) {
      fireEvent.click(zoomInBtn);
    }
    expect(screen.getByText("500%")).toBeInTheDocument();
    expect(zoomInBtn).toBeDisabled();

    // Zoom out back down
    fireEvent.click(zoomOutBtn);
    expect(screen.getByText("450%")).toBeInTheDocument();
    expect(zoomInBtn).not.toBeDisabled();
  });

  it("handles wheel zoom in and zoom out", () => {
    render(<MapViewerModal isOpen={true} onClose={vi.fn()} maps={sampleMaps} />);

    const viewport = screen.getByTestId("map-viewport");
    expect(viewport).toBeInTheDocument();

    // Wheel up -> Zoom in
    fireEvent.wheel(viewport, { deltaY: -100 });
    expect(screen.getByText("150%")).toBeInTheDocument();

    // Wheel down -> Zoom out
    fireEvent.wheel(viewport, { deltaY: 100 });
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("handles rotation and reset view", () => {
    render(<MapViewerModal isOpen={true} onClose={vi.fn()} maps={sampleMaps} />);

    const rotateBtn = screen.getByLabelText("Rotate 90°");
    const resetBtn = screen.getByLabelText("Reset View");
    const zoomInBtn = screen.getByLabelText("Zoom In");

    // Zoom in and rotate
    fireEvent.click(zoomInBtn);
    fireEvent.click(rotateBtn);

    const transformDiv = screen.getByTestId("map-transform");
    expect(transformDiv).toHaveStyle({
      transform: "translate3d(0px, 0px, 0px) scale(1.5) rotate(90deg)",
    });
    expect(screen.getByText("150%")).toBeInTheDocument();

    // Reset view
    fireEvent.click(resetBtn);
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(transformDiv).toHaveStyle({
      transform: "translate3d(0px, 0px, 0px) scale(1) rotate(0deg)",
    });
  });

  it("navigates between multiple maps with next/prev buttons", () => {
    render(<MapViewerModal isOpen={true} onClose={vi.fn()} maps={sampleMaps} initialIndex={0} />);

    // Initial map is index 0
    expect(screen.getByText("Middle-earth West")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();

    const prevBtn = screen.getByLabelText("Previous Map");
    const nextBtn = screen.getByLabelText("Next Map");

    expect(prevBtn).toBeDisabled();
    expect(nextBtn).not.toBeDisabled();

    // Advance to map index 1
    fireEvent.click(nextBtn);

    expect(screen.getByText("Mordor Regional Detail")).toBeInTheDocument();
    expect(screen.getByText(/1:250,000/)).toBeInTheDocument();
    expect(screen.getByText(/Mercator/)).toBeInTheDocument();
    expect(screen.getByText("2 / 2")).toBeInTheDocument();
    expect(nextBtn).toBeDisabled();
    expect(prevBtn).not.toBeDisabled();

    // Go back to map index 0
    fireEvent.click(prevBtn);
    expect(screen.getByText("Middle-earth West")).toBeInTheDocument();
    expect(screen.getByText("1 / 2")).toBeInTheDocument();
  });

  it("handles keyboard shortcuts for zoom, rotation, reset, and navigation", () => {
    render(<MapViewerModal isOpen={true} onClose={vi.fn()} maps={sampleMaps} initialIndex={0} />);

    // Press '+' to zoom in
    fireEvent.keyDown(window, { key: "+" });
    expect(screen.getByText("150%")).toBeInTheDocument();

    // Press 'r' to rotate
    fireEvent.keyDown(window, { key: "r" });
    const transformDiv = screen.getByTestId("map-transform");
    expect(transformDiv).toHaveStyle({
      transform: "translate3d(0px, 0px, 0px) scale(1.5) rotate(90deg)",
    });

    // Press '0' to reset
    fireEvent.keyDown(window, { key: "0" });
    expect(screen.getByText("100%")).toBeInTheDocument();

    // Press 'ArrowRight' to switch to next map
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(screen.getByText("Mordor Regional Detail")).toBeInTheDocument();

    // Press 'ArrowLeft' to switch back
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByText("Middle-earth West")).toBeInTheDocument();
  });

  it("rejects unsafe URLs such as javascript: or data: URIs", () => {
    const dangerousMaps: MapAttachmentItem[] = [
      {
        id: "bad-map",
        title: "Malicious Map",
        type: "world_map",
        image_url: "javascript:alert(1)",
      },
    ];

    render(<MapViewerModal isOpen={true} onClose={vi.fn()} maps={dangerousMaps} />);

    expect(screen.getByText("Malicious Map")).toBeInTheDocument();
    // Image should not be rendered with javascript: URL
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("No map image available for this supplement.")).toBeInTheDocument();
    // Open in new tab link should not be rendered
    expect(screen.queryByLabelText("Open Full Image in New Tab")).not.toBeInTheDocument();
  });
});
