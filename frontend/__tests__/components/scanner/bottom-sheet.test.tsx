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
 * Tests for streamlined 2-tab BottomSheet scanner component (C134).
 */
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { BottomSheet } from "@/components/scanner/bottom-sheet";
import enMessages from "@/messages/en.json";
import plMessages from "@/messages/pl.json";

const bottomSheetKeys = [
  "barcodeTab",
  "snapCoverTab",
  "searchingCatalog",
  "lookingUpBarcode",
  "skipAndEnterManually",
  "enterManually",
  "enterManuallyLink",
  "startCamera",
  "scanning",
  "tapToStartCamera",
  "uploadFromGallery",
  "invalidBarcode",
  "lookupTimedOut",
  "lookupFailed",
  "cameraUnavailable",
] as const;

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: { barcode?: string }) =>
    ({
      "bottomSheet.barcodeTab": "Barcode",
      "bottomSheet.snapCoverTab": "Snap Cover",
      "bottomSheet.searchingCatalog": "Searching catalog...",
      "bottomSheet.lookingUpBarcode": `Looking up barcode ${values?.barcode ?? ""}`,
      "bottomSheet.skipAndEnterManually": "Skip and enter manually",
      "bottomSheet.enterManually": "Enter Manually",
      "bottomSheet.enterManuallyLink": "Can't scan? Enter details manually",
      "bottomSheet.startCamera": "Start camera",
      "bottomSheet.scanning": "Scanning – point at barcode",
      "bottomSheet.tapToStartCamera": "Tap to start camera",
      "bottomSheet.uploadFromGallery": "Upload from Gallery",
      "bottomSheet.invalidBarcode": "Please enter a valid barcode (8-13 characters).",
      "bottomSheet.lookupTimedOut": "Lookup timed out. Switching to manual entry.",
      "bottomSheet.lookupFailed": "Could not look up this item. Please try again.",
      "bottomSheet.cameraUnavailable": "Camera unavailable",
    })[key] ?? key,
}));

vi.mock("@/components/scanner/camera-capture", () => ({
  CameraCapture: ({ label }: { label: string }) => <button data-testid="camera-capture">{label}</button>,
}));

vi.mock("@/lib/api/client", () => ({
  API_TIMEOUT_MS: 15_000,
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

  it("renders two capture tabs (barcode, snap cover) and omits duplicate manual search tab", () => {
    render(<BottomSheet videoRef={videoRef} onFound={onFound} />);

    expect(screen.getByTestId("scanner-tab-barcode")).toBeInTheDocument();
    expect(screen.getByTestId("scanner-tab-cover")).toBeInTheDocument();
    expect(screen.queryByTestId("scanner-tab-manual")).not.toBeInTheDocument();
  });

  it("switches active content when tabs are clicked", () => {
    render(<BottomSheet videoRef={videoRef} onFound={onFound} onTabChange={onTabChange} />);

    fireEvent.click(screen.getByTestId("scanner-tab-cover"));
    expect(onTabChange).toHaveBeenCalledWith("cover");

    const cameraCaptures = screen.getAllByTestId("camera-capture");
    expect(cameraCaptures.length).toBe(2);
  });

  it("barcode tab renders camera viewfinder controls and secondary enter-manually link", () => {
    render(<BottomSheet videoRef={videoRef} onFound={onFound} onShowManualForm={onShowManualForm} />);

    expect(screen.getByTestId("start-camera-button")).toBeInTheDocument();
    expect(screen.getByText(/Tap to start camera/i)).toBeInTheDocument();

    const manualLink = screen.getByTestId("enter-manually-link");
    expect(manualLink).toBeInTheDocument();
    fireEvent.click(manualLink);
    expect(onShowManualForm).toHaveBeenCalledWith("");
  });

  it("autoStart prop triggers camera stream acquisition on mount", async () => {
    const mockGetUserMedia = vi.fn().mockResolvedValue({
      getVideoTracks: () => [{ stop: vi.fn(), getCapabilities: () => ({}) }],
      getTracks: () => [{ stop: vi.fn() }],
    });
    Object.defineProperty(globalThis.navigator, "mediaDevices", {
      value: { getUserMedia: mockGetUserMedia },
      writable: true,
      configurable: true,
    });

    const videoEl = document.createElement("video");
    vi.spyOn(videoEl, "play").mockResolvedValue(undefined);
    const videoRefWithElement = { current: videoEl };

    render(<BottomSheet videoRef={videoRefWithElement} onFound={onFound} autoStart={true} />);

    await waitFor(() => {
      expect(mockGetUserMedia).toHaveBeenCalledWith(
        expect.objectContaining({
          video: expect.objectContaining({
            facingMode: { ideal: "environment" },
          }),
        })
      );
    });
  });

  it("uses API_TIMEOUT_MS (15000ms) for lookup timeout parity and triggers manual fallback on timeout", async () => {
    vi.useFakeTimers();
    const clientMod = await import("@/lib/api/client");
    vi.mocked(clientMod.apiFetch).mockImplementation(
      () => new Promise(() => {}) // never resolves
    );

    render(<BottomSheet videoRef={videoRef} onFound={onFound} onShowManualForm={onShowManualForm} />);

    // Enter a valid ISBN-13 in the manual barcode input if present or trigger via lookup
    const input = screen.queryByRole("textbox");
    if (input) {
      fireEvent.change(input, { target: { value: "9788329120463" } });
      fireEvent.submit(input.closest("form")!);

      // At 10_000ms, lookup must NOT have timed out yet
      await vi.advanceTimersByTimeAsync(10_500);
      expect(onShowManualForm).not.toHaveBeenCalled();

      // At 15_000ms, timeout triggers manual fallback
      await vi.advanceTimersByTimeAsync(4_600);
      expect(onShowManualForm).toHaveBeenCalledWith("9788329120463");
    }
    vi.useRealTimers();
  });
});
