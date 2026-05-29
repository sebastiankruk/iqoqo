// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//

/**
 * Unit tests for PrintQrCodeDialog.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { toast } from "sonner";
import { PrintQrCodeDialog } from "@/components/item/qrcode-dialog";
import type { Item } from "@/types/frbr";
import { apiClient } from "@/lib/api/client";

// Mock apiClient
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

// ── Fixtures ─────────────────────────────────────────────────────────────────

const baseItem: Item = {
  id: 42,
  manifestation_id: 10,
  status: "unread",
  collection_status: "available",
  is_owner: true,
  meta: { format: "book" },
  work: { id: 1, title: "The Hobbit", authors: ["J.R.R. Tolkien"] },
  expression: { id: 2, content_type: "text", language: "en" },
} as unknown as Item;

const noWorkItem: Item = {
  id: 7,
  manifestation_id: 3,
  status: "unread",
  collection_status: "available",
  is_owner: true,
  meta: {},
} as unknown as Item;

const noAuthorsItem: Item = {
  ...baseItem,
  id: 99,
  work: { id: 5, title: "Anonymous Work", authors: [] },
} as unknown as Item;

// ── Helpers ───────────────────────────────────────────────────────────────────

function makePrintWindowStub() {
  return {
    document: { write: vi.fn(), close: vi.fn() },
    print: vi.fn(),
    close: vi.fn(),
    onload: null as null | (() => void),
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PrintQrCodeDialog", () => {
  const fakeBlob = new Blob(["fake-png"], { type: "image/png" });

  beforeEach(() => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: fakeBlob });
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob://test-url");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // ── Closed state ────────────────────────────────────────────────────────────

  it("renders nothing when isOpen is false", () => {
    render(<PrintQrCodeDialog isOpen={false} onOpenChange={vi.fn()} item={baseItem} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  // ── Dialog structure ────────────────────────────────────────────────────────

  it("renders dialog with correct title when open", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Physical Copy Tracking Label")).toBeInTheDocument();
  });

  it("renders the dialog description", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    expect(screen.getByText(/Generate and print a QR code label/i)).toBeInTheDocument();
  });

  it("renders Download PNG and Print Label action buttons", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    expect(screen.getByText("Download PNG")).toBeInTheDocument();
    expect(screen.getByText("Print Label")).toBeInTheDocument();
  });

  // ── Item metadata display ────────────────────────────────────────────────────

  it("shows the work title inside the label preview", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    expect(screen.getByText("The Hobbit")).toBeInTheDocument();
  });

  it("shows the author line inside the label preview", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    expect(screen.getByText(/J\.R\.R\. Tolkien/)).toBeInTheDocument();
  });

  it("shows item ID and content type in the label preview", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    expect(screen.getByText(/iqoqo ID: #42/)).toBeInTheDocument();
    expect(screen.getByText(/text/i)).toBeInTheDocument();
  });

  it("shows 'Untitled' when item has no work or title", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={noWorkItem} />);
    expect(screen.getByText("Untitled")).toBeInTheDocument();
  });

  it("hides the author line when there are no authors", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={noAuthorsItem} />);
    expect(screen.queryByText(/^by /i)).not.toBeInTheDocument();
  });

  // ── QR image src ─────────────────────────────────────────────────────────────

  it("renders an <img> whose src points to the generated blob URL", async () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    const img = await screen.findByRole("img", { name: /QR Code/i });
    expect(img).toHaveAttribute("src", "blob://test-url");
    expect(apiClient.get).toHaveBeenCalledWith("/qrcode/42?format=png", expect.any(Object));
  });

  // ── Download PNG ─────────────────────────────────────────────────────────────

  it("calls apiClient and creates an object URL when Download PNG is clicked", async () => {
    const realCreateElement = document.createElement.bind(document);
    let capturedLink: HTMLAnchorElement | null = null;
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = realCreateElement(tag);
      if (tag === "a") {
        capturedLink = el as HTMLAnchorElement;
        vi.spyOn(capturedLink, "click").mockImplementation(() => undefined);
      }
      return el;
    });

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Download PNG/i })).not.toBeDisabled();
    });
    const downloadBtn = screen.getByRole("button", { name: /Download PNG/i });
    
    fireEvent.click(downloadBtn);

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith("/qrcode/42?format=png", expect.any(Object));
      expect(capturedLink).not.toBeNull();
      expect(capturedLink!.download).toBe("iqoqo-qr-item-42.png");
      expect(capturedLink!.href).toBe("blob://test-url");
    });
  });

  it("shows toast.error when Download PNG fetch throws an error", async () => {
    vi.mocked(apiClient.get).mockRejectedValueOnce(new Error("Network failure"));

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Failed to load QR code image.");
    });
  });

  // ── Print Label ──────────────────────────────────────────────────────────────

  it("opens a new window and writes item data to it on Print Label click", async () => {
    const printStub = makePrintWindowStub();
    const openSpy = vi.spyOn(window, "open").mockReturnValue(printStub as unknown as Window);

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Print Label/i })).not.toBeDisabled();
    });
    const printBtn = screen.getByRole("button", { name: /Print Label/i });

    fireEvent.click(printBtn);

    expect(openSpy).toHaveBeenCalledWith("", "_blank");
    expect(printStub.document.write).toHaveBeenCalledTimes(1);

    const writtenHtml: string = printStub.document.write.mock.calls[0][0];
    expect(writtenHtml).toContain("The Hobbit");
    expect(writtenHtml).toContain("J.R.R. Tolkien");
    expect(writtenHtml).toContain("iqoqo ID: #42");
    expect(writtenHtml).toContain("text");
    expect(writtenHtml).toContain("blob://test-url");
  });

  it("shows toast.error when the print popup is blocked", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Print Label/i })).not.toBeDisabled();
    });
    const printBtn = screen.getByRole("button", { name: /Print Label/i });

    fireEvent.click(printBtn);

    expect(toast.error).toHaveBeenCalledWith("Popup blocked! Please allow popups to print.");
  });

  // ── onOpenChange callback ────────────────────────────────────────────────────

  it("calls onOpenChange when the dialog is dismissed", () => {
    const onOpenChange = vi.fn();
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={onOpenChange} item={baseItem} />);
    fireEvent.keyDown(document.body, { key: "Escape", code: "Escape" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
