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
import { describe, it, expect, vi, afterEach } from "vitest";
import ScanPage from "@/app/scan/page";
import * as hooks from "@/lib/api/hooks";

vi.mock("next/navigation", () => ({
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

vi.mock("@/lib/api/hooks", () => ({
  useAddManualItem: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock the components so we don't need their full implementation
vi.mock("@/components/scanner/top-bar", () => ({ TopBar: () => <div data-testid="top-bar" /> }));
vi.mock("@/components/scanner/viewfinder", () => ({ Viewfinder: () => <div data-testid="viewfinder" /> }));
vi.mock("@/components/scanner/bottom-sheet", () => ({
  BottomSheet: ({ onShowManualForm }: { onShowManualForm?: () => void }) => (
    <div data-testid="bottom-sheet">
      <button onClick={onShowManualForm}>Cannot find barcode? Enter Manually</button>
    </div>
  ),
}));
vi.mock("@/components/scanner/success-card", () => ({ SuccessCard: () => <div data-testid="success-card" /> }));

describe("ScanPage", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders scanner components initially", () => {
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);

    render(<ScanPage />);
    expect(screen.getByTestId("top-bar")).toBeInTheDocument();
    expect(screen.getByTestId("viewfinder")).toBeInTheDocument();
    expect(screen.getByTestId("bottom-sheet")).toBeInTheDocument();
  });

  it("shows manual entry form when 'Enter Manually' is clicked", () => {
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);

    render(<ScanPage />);

    // Check toggle button
    const toggleButton = screen.getByText(/Cannot find barcode\? Enter Manually/i);
    expect(toggleButton).toBeInTheDocument();

    // Click toggle button
    fireEvent.click(toggleButton);

    // Form should appear
    expect(screen.getByText(/Manual Entry/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Author \/ Creator/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Format/i)).toBeInTheDocument();
  });

  it("calls mutate with form data when submitting manual entry", () => {
    const mutateMock = vi.fn();
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: mutateMock,
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);

    render(<ScanPage />);

    // Open form
    fireEvent.click(screen.getByText(/Cannot find barcode\? Enter Manually/i));

    // Fill out form
    fireEvent.change(screen.getByLabelText(/Title/i), { target: { value: "Test Title" } });
    fireEvent.change(screen.getByLabelText(/Author \/ Creator/i), { target: { value: "Test Author" } });
    fireEvent.change(screen.getByLabelText(/Format/i), { target: { value: "sound" } });

    // Submit form
    fireEvent.click(screen.getByText(/Add to Library/i));

    // Assert mutate was called
    expect(mutateMock).toHaveBeenCalledTimes(1);
    expect(mutateMock).toHaveBeenCalledWith(
      { Title: "Test Title", Authors: ["Test Author"], Format: "sound" },
      expect.any(Object)
    );
  });
});
