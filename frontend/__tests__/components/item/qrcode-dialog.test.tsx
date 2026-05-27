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

/**
 * Unit tests for PrintQrCodeDialog.
 *
 * Covers:
 *  - closed state (dialog not mounted)
 *  - dialog renders with correct title / description
 *  - item title, author, ID, and content type displayed correctly
 *  - "Untitled" fallback when no work title present
 *  - author line hidden when no authors
 *  - Download PNG: fetch called, <a> link triggered, blob URL created/revoked
 *  - Download PNG: toast.error shown on network failure
 *  - Print Label: window.open called, document.write contains item data
 *  - Print Label: toast.error shown when popup is blocked
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { toast } from "sonner";
import { PrintQrCodeDialog } from "@/components/item/qrcode-dialog";
import type { Item } from "@/types/frbr";

// ── Fixtures ─────────────────────────────────────────────────────────────────

/** A fully populated item owned by the current user. */
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

/** Item with no work information (bare minimum). */
const noWorkItem: Item = {
  id: 7,
  manifestation_id: 3,
  status: "unread",
  collection_status: "available",
  is_owner: true,
  meta: {},
} as unknown as Item;

/** Item with a work but no authors. */
const noAuthorsItem: Item = {
  ...baseItem,
  id: 99,
  work: { id: 5, title: "Anonymous Work", authors: [] },
} as unknown as Item;

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Creates a minimal stub for the window.open print popup.
 * @returns A stub object compatible with the print popup usage in the component.
 */
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

  it("renders an <img> whose src points to the qrcode API endpoint", () => {
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    const img = screen.getByRole("img", { name: /QR Code/i });
    expect(img).toHaveAttribute("src", expect.stringContaining("/qrcode/42"));
    expect(img).toHaveAttribute("src", expect.stringContaining("format=png"));
  });

  // ── Download PNG ─────────────────────────────────────────────────────────────

  it("calls fetch and creates an object URL when Download PNG is clicked", async () => {
    const blobMock = new Blob(["fake-png"], { type: "image/png" });
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      blob: () => Promise.resolve(blobMock),
    });
    const createObjectURLSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob://test-url");
    const revokeObjectURLSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

    // Track the anchor link created by the component by watching createElement.
    // Capture the REAL createElement before mocking to avoid infinite recursion.
    const realCreateElement = document.createElement.bind(document);
    let capturedLink: HTMLAnchorElement | null = null;
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = realCreateElement(tag);
      if (tag === "a") {
        capturedLink = el as HTMLAnchorElement;
        // Prevent actual navigation when click() is called
        vi.spyOn(capturedLink, "click").mockImplementation(() => undefined);
      }
      return el;
    });

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    fireEvent.click(screen.getByText("Download PNG"));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining("/qrcode/42"));
      expect(createObjectURLSpy).toHaveBeenCalledWith(blobMock);
      expect(capturedLink).not.toBeNull();
      expect(capturedLink!.download).toBe("iqoqo-qr-item-42.png");
      expect(capturedLink!.href).toBe("blob://test-url");
      expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob://test-url");
    });
  });

  it("shows toast.error when Download PNG fetch returns a non-ok response", async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({ ok: false });

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    fireEvent.click(screen.getByText("Download PNG"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Failed to download QR code image.");
    });
  });

  it("shows toast.error when Download PNG fetch throws a network error", async () => {
    global.fetch = vi.fn().mockRejectedValueOnce(new Error("Network failure"));

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    fireEvent.click(screen.getByText("Download PNG"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Failed to download QR code image.");
    });
  });

  // ── Print Label ──────────────────────────────────────────────────────────────

  it("opens a new window and writes item data to it on Print Label click", () => {
    const printStub = makePrintWindowStub();
    const openSpy = vi.spyOn(window, "open").mockReturnValue(printStub as unknown as Window);

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    fireEvent.click(screen.getByText("Print Label"));

    expect(openSpy).toHaveBeenCalledWith("", "_blank");
    expect(printStub.document.write).toHaveBeenCalledTimes(1);

    const writtenHtml: string = printStub.document.write.mock.calls[0][0];
    expect(writtenHtml).toContain("The Hobbit");
    expect(writtenHtml).toContain("J.R.R. Tolkien");
    expect(writtenHtml).toContain("iqoqo ID: #42");
    expect(writtenHtml).toContain("text");
  });

  it("includes the QR image src in the print HTML", () => {
    const printStub = makePrintWindowStub();
    vi.spyOn(window, "open").mockReturnValue(printStub as unknown as Window);

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    fireEvent.click(screen.getByText("Print Label"));

    const writtenHtml: string = printStub.document.write.mock.calls[0][0];
    expect(writtenHtml).toContain("/qrcode/42");
  });

  it("does not include author line in print HTML when no authors", () => {
    const printStub = makePrintWindowStub();
    vi.spyOn(window, "open").mockReturnValue(printStub as unknown as Window);

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={noAuthorsItem} />);
    fireEvent.click(screen.getByText("Print Label"));

    const writtenHtml: string = printStub.document.write.mock.calls[0][0];
    // Author div should not appear in print output
    expect(writtenHtml).not.toContain(`class="author"`);
  });

  it("shows toast.error when the print popup is blocked", () => {
    vi.spyOn(window, "open").mockReturnValue(null);

    render(<PrintQrCodeDialog isOpen={true} onOpenChange={vi.fn()} item={baseItem} />);
    fireEvent.click(screen.getByText("Print Label"));

    expect(toast.error).toHaveBeenCalledWith("Popup blocked! Please allow popups to print.");
  });

  // ── onOpenChange callback ────────────────────────────────────────────────────

  it("calls onOpenChange when the dialog is dismissed", () => {
    const onOpenChange = vi.fn();
    render(<PrintQrCodeDialog isOpen={true} onOpenChange={onOpenChange} item={baseItem} />);
    // Trigger close via Escape key (Radix Dialog handles this internally)
    fireEvent.keyDown(document.body, { key: "Escape", code: "Escape" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
