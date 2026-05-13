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
// along with this program.  If not, see <https://www.https://www.gnu.org/licenses/>
//

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ShareButton } from "@/components/ui/share-button";
import { toast } from "sonner";

// Mock next-intl
vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key === "share" ? "Share" : key,
}));

describe("ShareButton", () => {
  const mockUrl = "https://example.com";
  const mockTitle = "Test Title";

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock navigator.clipboard
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
      configurable: true,
    });
    // Ensure navigator.share is undefined by default for fallback testing
    Object.defineProperty(navigator, "share", {
      value: undefined,
      configurable: true,
    });
  });

  it("renders with share text", () => {
    render(<ShareButton url={mockUrl} title={mockTitle} />);
    expect(screen.getByText("Share")).toBeInTheDocument();
  });

  it("calls navigator.share when available", async () => {
    const shareSpy = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", {
      value: shareSpy,
      configurable: true,
    });

    render(<ShareButton url={mockUrl} title={mockTitle} />);
    fireEvent.click(screen.getByRole("button"));

    expect(shareSpy).toHaveBeenCalledWith({
      title: mockTitle,
      text: undefined,
      url: mockUrl,
    });
  });

  it("falls back to clipboard when navigator.share is unavailable", async () => {
    render(<ShareButton url={mockUrl} title={mockTitle} />);
    fireEvent.click(screen.getByRole("button"));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockUrl);
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalled();
    });
  });
});
