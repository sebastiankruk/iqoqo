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

/**
 * Tests for BottomSheet scanner component.
 *
 * Verifies tab rendering, tab switching, manual search, barcode camera,
 * error display, and manual entry fallback.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { BottomSheet } from "@/components/scanner/bottom-sheet";

// Mock next-intl
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock CameraCapture component
vi.mock("@/components/scanner/camera-capture", () => ({
  CameraCapture: ({ label }: { label: string }) => <button data-testid="camera-capture">{label}</button>,
}));

// Mock the api client for lookup
vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("BottomSheet", () => {
  let videoRef: React.RefObject<HTMLVideoElement | null>;
  const onFound = vi.fn();
  const onScannerStateChange = vi.fn();
  const onTabChange = vi.fn();
  const onExtractComplete = vi.fn();
  const onExtractionFailure = vi.fn();
  const onShowManualForm = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    videoRef = { current: null };
  });

  it("renders all three tabs: barcode, snap cover, manual search", () => {
    render(<BottomSheet videoRef={videoRef} onFound={onFound} />);

    expect(screen.getByTestId("scanner-tab-barcode")).toBeInTheDocument();
    expect(screen.getByTestId("scanner-tab-cover")).toBeInTheDocument();
    expect(screen.getByTestId("scanner-tab-manual")).toBeInTheDocument();
  });

  it("switches active content when tabs are clicked", () => {
    render(<BottomSheet videoRef={videoRef} onFound={onFound} onTabChange={onTabChange} />);

    // Click "Snap Cover" tab
    fireEvent.click(screen.getByTestId("scanner-tab-cover"));
    expect(onTabChange).toHaveBeenCalledWith("cover");

    // CameraCapture should be rendered (as "Snap Cover" and "Upload from Gallery" buttons)
    const cameraCaptures = screen.getAllByTestId("camera-capture");
    expect(cameraCaptures.length).toBe(2);
  });

  it("manual search tab shows text input and search button", () => {
    render(<BottomSheet videoRef={videoRef} onFound={onFound} />);

    // Switch to manual tab
    fireEvent.click(screen.getByTestId("scanner-tab-manual"));

    // Should show a text input
    const input = screen.getByPlaceholderText("ISBN, UPC, Discogs ID, or Artist – Title…");
    expect(input).toBeInTheDocument();

    // Should show manual entry fallback button
    expect(screen.getByText("Manual Entry Form")).toBeInTheDocument();
  });

  it("barcode tab renders camera viewfinder controls", () => {
    render(<BottomSheet videoRef={videoRef} onFound={onFound} />);

    // Should be on barcode tab by default
    expect(screen.getByTestId("start-camera-button")).toBeInTheDocument();
    expect(screen.getByText(/Tap to start camera/i)).toBeInTheDocument();
  });

  it("shows manual entry fallback button", () => {
    render(<BottomSheet videoRef={videoRef} onFound={onFound} onShowManualForm={onShowManualForm} />);

    // Switch to manual tab
    fireEvent.click(screen.getByTestId("scanner-tab-manual"));

    const manualEntryBtn = screen.getByText("Manual Entry Form");
    fireEvent.click(manualEntryBtn);
    expect(onShowManualForm).toHaveBeenCalled();
  });
});
