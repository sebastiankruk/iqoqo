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
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ScanPage from "@/app/scan/page";
import * as hooks from "@/lib/api/hooks";
import * as apiClient from "@/lib/api/client";

vi.mock("@/lib/api/escalations", () => ({
  useCreateNewMediaTypeEscalation: () => ({
    mutate: vi.fn(),
    isPending: false,
    isSuccess: false,
  }),
}));

vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

vi.mock("@/lib/api/hooks", () => ({
  useAddManualItem: vi.fn(),
  useAppConfig: vi.fn(() => ({ data: { federation_head_mode: false }, isLoading: false })),
}));

vi.mock("@/lib/api/hooks/catalog", () => ({
  useAppConfig: vi.fn(() => ({ data: { federation_head_mode: false }, isLoading: false })),
}));

const mockEnqueueOffline = vi.fn();
vi.mock("@/lib/capacitor/offline-cache", () => ({
  findOfflineDuplicate: vi.fn(),
  enqueueOfflineManualEntry: (...args: any[]) => mockEnqueueOffline(...args),
  flushOfflineManualQueue: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Mock the components so we don't need their full implementation
let mockSetMediaType: (val: string) => void;
let mockSetPolicy: (val: string) => void;

vi.mock("@/components/scanner/top-bar", () => ({
  TopBar: (props: any) => {
    mockSetMediaType = props.setFormat;
    mockSetPolicy = props.setPolicy;
    return <div data-testid="top-bar">{props.children}</div>;
  },
}));

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
  beforeEach(() => {
    let store: Record<string, string> = {};
    const mockLocalStorage = {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, value: string) => {
        store[key] = value.toString();
      },
      removeItem: (key: string) => {
        delete store[key];
      },
      clear: () => {
        store = {};
      },
    };
    Object.defineProperty(window, "localStorage", {
      value: mockLocalStorage,
      writable: true,
      configurable: true,
    });
  });

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
    expect(screen.getByText(/Manual Item Entry/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Creator\(s\)/i)).toBeInTheDocument();
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
    fireEvent.change(screen.getByLabelText(/Creator\(s\)/i), { target: { value: "Test Author" } });
    fireEvent.change(screen.getByLabelText(/Format/i), { target: { value: "music" } });

    // Submit form
    fireEvent.click(screen.getByText(/Save Manual Entry/i));

    // Assert mutate was called
    expect(mutateMock).toHaveBeenCalledTimes(1);
    expect(mutateMock).toHaveBeenCalledWith(
      expect.objectContaining({ Title: "Test Title", Authors: ["Test Author"], Format: "music" }),
      expect.any(Object)
    );
  });

  it("updates localStorage when media type and policy change", () => {
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);

    const setItemSpy = vi.spyOn(window.localStorage, "setItem");

    render(<ScanPage />);

    // Trigger state changes
    act(() => {
      if (mockSetMediaType) {
        mockSetMediaType("movie");
      }
      if (mockSetPolicy) {
        mockSetPolicy("catalog");
      }
    });

    // Verify localStorage was updated
    expect(setItemSpy).toHaveBeenCalledWith("iqoqo_scanner_media_type", "movie");
    expect(setItemSpy).toHaveBeenCalledWith("iqoqo_scanner_policy", "catalog");

    setItemSpy.mockRestore();
  });

  it("renders unified lookup input and batch mode toggle", () => {
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);

    render(<ScanPage />);

    expect(screen.getByTestId("unified-lookup-input")).toBeInTheDocument();
    expect(screen.getByTestId("unified-lookup-submit")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /batch mode/i })).toBeInTheDocument();
  });

  it("toggles batch mode button state on click", () => {
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);

    render(<ScanPage />);

    const batchButton = screen.getByRole("button", { name: /batch mode/i });
    expect(batchButton).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(batchButton);
    expect(batchButton).toHaveAttribute("aria-pressed", "true");
  });

  it("passes ?format=lego when quick lookup is submitted with LEGO media type selected", async () => {
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);
    vi.mocked(apiClient.apiFetch).mockResolvedValue({
      title: "LEGO Speed Champions 77256",
      barcode: "5702018068229",
      format: "standard_set",
    } as any);

    render(<ScanPage />);

    act(() => {
      if (mockSetMediaType) {
        mockSetMediaType("lego");
      }
    });

    const input = screen.getByTestId("unified-lookup-input");
    fireEvent.change(input, { target: { value: "5702018068229" } });
    fireEvent.click(screen.getByTestId("unified-lookup-submit"));

    await waitFor(() => {
      expect(apiClient.apiFetch).toHaveBeenCalledWith("/lookup/5702018068229?format=lego");
    });
  });

  it("displays toast error and does not enqueue offline when manual submission fails with server error", async () => {
    let capturedOptions: any;
    const mutateMock = vi.fn().mockImplementation((payload, options) => {
      capturedOptions = options;
    });
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: mutateMock,
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);

    render(<ScanPage />);

    // Open form & submit
    fireEvent.click(screen.getByText(/Cannot find barcode\? Enter Manually/i));
    fireEvent.change(screen.getByLabelText(/Title/i), { target: { value: "Rejected Book" } });
    fireEvent.click(screen.getByText(/Save Manual Entry/i));

    // Simulate online HTTP 403 response
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(true);
    await act(async () => {
      await capturedOptions.onError({
        response: { status: 403, data: { error: "Physical items disabled in showcase mode" } },
      });
    });

    const { toast } = await import("sonner");
    expect(toast.error).toHaveBeenCalledWith("Error: Physical items disabled in showcase mode");
    expect(mockEnqueueOffline).not.toHaveBeenCalled();
  });

  it("enqueues offline manual entry when offline during submission", async () => {
    let capturedOptions: any;
    const mutateMock = vi.fn().mockImplementation((payload, options) => {
      capturedOptions = options;
    });
    vi.mocked(hooks.useAddManualItem).mockReturnValue({
      mutate: mutateMock,
      isPending: false,
    } as unknown as ReturnType<typeof hooks.useAddManualItem>);

    render(<ScanPage />);

    fireEvent.click(screen.getByText(/Cannot find barcode\? Enter Manually/i));
    fireEvent.change(screen.getByLabelText(/Title/i), { target: { value: "Offline Flea Market Book" } });
    fireEvent.click(screen.getByText(/Save Manual Entry/i));

    // Simulate network offline
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    await act(async () => {
      await capturedOptions.onError(new Error("Network Error"));
    });

    const { toast } = await import("sonner");
    expect(mockEnqueueOffline).toHaveBeenCalledWith(expect.objectContaining({ Title: "Offline Flea Market Book" }));
    expect(toast.info).toHaveBeenCalledWith(
      expect.stringContaining('Network unreachable: "Offline Flea Market Book" queued locally')
    );
  });
});
