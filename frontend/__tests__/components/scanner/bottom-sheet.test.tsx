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

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BottomSheet } from "@/components/scanner/bottom-sheet";

// Mock next-intl
vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: () => (key: string) => key,
}));

// Mock CameraCapture to simplify rendering
vi.mock("@/components/scanner/camera-capture", () => ({
  CameraCapture: vi.fn(({ label }: { label: string }) => <div data-testid="camera-capture-mock">{label}</div>),
}));

function createMockRef() {
  return { current: null } as React.RefObject<HTMLVideoElement | null>;
}

describe("BottomSheet", () => {
  it("renders three tabs: Barcode, Snap Cover, Manual Search", () => {
    render(<BottomSheet videoRef={createMockRef()} onFound={vi.fn()} />);
    expect(screen.getByText("Barcode")).toBeTruthy();
    expect(screen.getByText("Snap Cover")).toBeTruthy();
    expect(screen.getByText("Manual Search")).toBeTruthy();
  });

  it("shows start camera button in barcode tab by default", () => {
    render(<BottomSheet videoRef={createMockRef()} onFound={vi.fn()} />);
    expect(screen.getByTestId("start-camera-button")).toBeTruthy();
  });

  it("switches to cover tab and shows CameraCapture components", () => {
    render(<BottomSheet videoRef={createMockRef()} onFound={vi.fn()} />);
    fireEvent.click(screen.getByTestId("scanner-tab-cover"));
    const captures = screen.getAllByTestId("camera-capture-mock");
    expect(captures.length).toBeGreaterThanOrEqual(1);
  });

  it("switches to manual tab and shows search input", () => {
    render(<BottomSheet videoRef={createMockRef()} onFound={vi.fn()} />);
    fireEvent.click(screen.getByText("Manual Search"));
    expect(screen.getByPlaceholderText("ISBN, UPC, Discogs ID, or Artist – Title…")).toBeTruthy();
  });

  it("calls onTabChange callback when switching tabs", () => {
    const onTabChange = vi.fn();
    render(<BottomSheet videoRef={createMockRef()} onFound={vi.fn()} onTabChange={onTabChange} />);
    fireEvent.click(screen.getByText("Snap Cover"));
    expect(onTabChange).toHaveBeenCalledWith("cover");
  });
});
