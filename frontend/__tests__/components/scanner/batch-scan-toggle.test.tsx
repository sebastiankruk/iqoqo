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
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, renderHook, act } from "@testing-library/react";
import { BatchScanToggle, useBatchMode, BatchScannedItem } from "@/components/scanner/batch-scan-toggle";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: { count?: number; title?: string }) => {
    const map: Record<string, string> = {
      "batchMode.toggleLabel": "Batch mode",
      "batchMode.viewQueue": "View scanned batch queue",
      "batchMode.recentScans": `Recent scans (${params?.count ?? 0})`,
      "batchMode.clearQueue": "Clear queue",
      "batchMode.itemAddedToast": `Added "${params?.title ?? ""}" to collection`,
    };
    return map[key] || key;
  },
}));

vi.mock("@/lib/capacitor/haptics", () => ({
  triggerScanHaptic: vi.fn(),
  triggerSuccessHaptic: vi.fn(),
  triggerErrorHaptic: vi.fn(),
}));

describe("useBatchMode Hook", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it("initializes with batch mode disabled and empty queue", () => {
    const { result } = renderHook(() => useBatchMode());
    expect(result.current.isBatchMode).toBe(false);
    expect(result.current.scannedQueue).toEqual([]);
  });

  it("toggles and persists batch mode state to localStorage", () => {
    const { result } = renderHook(() => useBatchMode());

    act(() => {
      result.current.toggleBatchMode();
    });
    expect(result.current.isBatchMode).toBe(true);
    expect(window.localStorage.getItem("iqoqo_batch_scan_mode")).toBe("true");

    act(() => {
      result.current.toggleBatchMode();
    });
    expect(result.current.isBatchMode).toBe(false);
    expect(window.localStorage.getItem("iqoqo_batch_scan_mode")).toBe("false");
  });

  it("records scanned items and triggers callback", () => {
    const onItemAdded = vi.fn();
    const { result } = renderHook(() => useBatchMode({ onItemAdded }));

    act(() => {
      result.current.recordScan("9780451524935", {
        title: "1984",
        authors: ["George Orwell"],
        id: 42,
      });
    });

    expect(result.current.scannedQueue).toHaveLength(1);
    expect(result.current.scannedQueue[0].isbn).toBe("9780451524935");
    expect(result.current.scannedQueue[0].title).toBe("1984");
    expect(onItemAdded).toHaveBeenCalledTimes(1);
  });

  it("handles consecutive-barcode cooldown debounce", () => {
    const { result } = renderHook(() => useBatchMode({ cooldownMs: 1500 }));

    act(() => {
      result.current.recordScan("9780141439518", { title: "Pride and Prejudice" });
    });

    // Immediate re-scan of identical barcode is in cooldown
    expect(result.current.isCooldownActive("9780141439518")).toBe(true);

    // Different barcode is NOT in cooldown
    expect(result.current.isCooldownActive("9780061120084")).toBe(false);
  });

  it("clears the batch queue and resets cooldown", () => {
    const { result } = renderHook(() => useBatchMode());

    act(() => {
      result.current.recordScan("123", { title: "Item 1" });
      result.current.clearQueue();
    });

    expect(result.current.scannedQueue).toEqual([]);
    expect(result.current.isCooldownActive("123")).toBe(false);
  });
});

describe("BatchScanToggle Component", () => {
  it("renders button with correct label and toggles on click", () => {
    const onToggle = vi.fn();
    render(<BatchScanToggle enabled={false} onToggle={onToggle} />);

    const button = screen.getByRole("button", { name: /batch mode/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(button);
    expect(onToggle).toHaveBeenCalledWith(true);
  });

  it("renders active pressed state and queue count badge", () => {
    render(<BatchScanToggle enabled={true} onToggle={vi.fn()} queueCount={5} />);

    const button = screen.getByRole("button", { name: /batch mode/i });
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("renders queue popover trigger when items exist", () => {
    const recent: BatchScannedItem[] = [
      { id: 1, isbn: "123", title: "Dune", authors: ["Frank Herbert"], timestamp: Date.now() },
    ];
    render(
      <BatchScanToggle enabled={true} onToggle={vi.fn()} queueCount={1} recentItems={recent} onClearQueue={vi.fn()} />
    );

    const queueButton = screen.getByRole("button", { name: /view scanned batch queue/i });
    expect(queueButton).toBeInTheDocument();
  });
});
