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
import enMessages from "@/messages/en.json";
import plMessages from "@/messages/pl.json";

const bottomSheetKeys = [
  "barcodeTab",
  "snapCoverTab",
  "manualSearchTab",
  "searchingCatalog",
  "lookingUpBarcode",
  "skipAndEnterManually",
  "enterManually",
  "startCamera",
  "scanning",
  "tapToStartCamera",
  "uploadFromGallery",
  "manualSearchPlaceholder",
  "lookingUp",
  "manualSearchHint",
  "manualEntryForm",
  "invalidBarcode",
  "lookupTimedOut",
  "lookupFailed",
  "cameraUnavailable",
] as const;

// Mock next-intl
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: { barcode?: string }) =>
    ({
      "bottomSheet.barcodeTab": "Barcode",
      "bottomSheet.snapCoverTab": "Snap Cover",
      "bottomSheet.manualSearchTab": "Manual Search",
      "bottomSheet.searchingCatalog": "Searching catalog...",
      "bottomSheet.lookingUpBarcode": `Looking up barcode ${values?.barcode ?? ""}`,
      "bottomSheet.skipAndEnterManually": "Skip and enter manually",
      "bottomSheet.enterManually": "Enter Manually",
      "bottomSheet.startCamera": "Start camera",
      "bottomSheet.scanning": "Scanning – point at barcode",
      "bottomSheet.tapToStartCamera": "Tap to start camera",
      "bottomSheet.snapCover": "Snap Cover",
      "bottomSheet.uploadFromGallery": "Upload from Gallery",
      "bottomSheet.manualSearchPlaceholder": "ISBN, UPC, Discogs ID, or Artist – Title…",
      "bottomSheet.lookingUp": "Looking up…",
      "bottomSheet.manualSearchHint": "Enter barcode, Discogs Release ID, or Artist – Title",
      "bottomSheet.manualEntryForm": "Manual Entry Form",
      "bottomSheet.invalidBarcode": "Please enter a valid barcode (8-13 characters).",
      "bottomSheet.lookupTimedOut": "Lookup timed out. Switching to manual entry.",
      "bottomSheet.lookupFailed": "Could not look up this item. Please try again.",
      "bottomSheet.cameraUnavailable": "Camera unavailable",
    })[key] ?? key,
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
  const onTabChange = vi.fn();
  const onShowManualForm = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    videoRef = { current: null };
  });

  it("has complete English and Polish bottom-sheet translations", () => {
    for (const key of bottomSheetKeys) {
      expect(enMessages.scanner.bottomSheet[key]).toBeTruthy();
      expect(plMessages.scanner.bottomSheet[key]).toBeTruthy();
    }
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

  it("automatically calls onShowManualForm when manual search lookup fails", async () => {
    const { apiFetch } = await import("@/lib/api/client");
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("Lookup failed"));

    render(<BottomSheet videoRef={videoRef} onFound={onFound} onShowManualForm={onShowManualForm} />);

    // Switch to manual tab
    fireEvent.click(screen.getByTestId("scanner-tab-manual"));

    const input = screen.getByPlaceholderText("ISBN, UPC, Discogs ID, or Artist – Title…");
    fireEvent.change(input, { target: { value: "9781234567890" } });

    const form = input.closest("form");
    if (form) {
      fireEvent.submit(form);
    }

    await screen.findByText("Lookup failed");
    expect(onShowManualForm).toHaveBeenCalledWith("9781234567890");
  });

  it("renders skip button in searching overlay and invokes onShowManualForm on click", async () => {
    const { apiFetch } = await import("@/lib/api/client");
    vi.mocked(apiFetch).mockReturnValueOnce(new Promise(() => {}));

    render(<BottomSheet videoRef={videoRef} onFound={onFound} onShowManualForm={onShowManualForm} />);

    // Switch to manual tab and submit search
    fireEvent.click(screen.getByTestId("scanner-tab-manual"));
    const input = screen.getByPlaceholderText("ISBN, UPC, Discogs ID, or Artist – Title…");
    fireEvent.change(input, { target: { value: "9780140449136" } });
    const form = input.closest("form");
    if (form) {
      fireEvent.submit(form);
    }

    // Searching overlay should be visible
    expect(screen.getByTestId("scanner-searching-overlay")).toBeInTheDocument();
    const skipBtn = screen.getByTestId("scanner-skip-manual-button");
    expect(skipBtn).toBeInTheDocument();
    expect(skipBtn).toHaveTextContent("Skip and enter manually");

    // Clicking skip should trigger onShowManualForm with the searched barcode
    fireEvent.click(skipBtn);
    expect(onShowManualForm).toHaveBeenCalledWith("9780140449136");
  });
});
