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

import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createAppQueryClient, Providers } from "@/components/providers";

// Mock sonner Toaster to inspect passed props
vi.mock("sonner", () => ({
  Toaster: vi.fn(({ position, mobileOffset }) => (
    <div data-testid="mock-toaster" data-position={position} data-mobile-offset={JSON.stringify(mobileOffset)} />
  )),
}));

describe("Providers Component", () => {
  const originalInnerWidth = window.innerWidth;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: originalInnerWidth,
    });
  });

  it("sets a 60-second default query stale time and preserves query-level overrides", () => {
    const client = createAppQueryClient();
    expect(client.getDefaultOptions().queries).toMatchObject({ staleTime: 60_000, retry: 1 });
    expect(client.defaultQueryOptions({ queryKey: ["volatile"], staleTime: 0 }).staleTime).toBe(0);
  });

  it("renders children successfully", () => {
    render(
      <Providers>
        <div data-testid="child-element">Test Content</div>
      </Providers>
    );

    expect(screen.getByTestId("child-element")).toBeInTheDocument();
    expect(screen.getByText("Test Content")).toBeInTheDocument();
  });

  it("positions Toaster at bottom-right on desktop viewport (>= 640px)", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1024,
    });

    render(
      <Providers>
        <span>Content</span>
      </Providers>
    );

    const toaster = screen.getByTestId("mock-toaster");
    expect(toaster).toHaveAttribute("data-position", "bottom-right");
  });

  it("positions Toaster at top-center on mobile viewport (< 640px) to prevent bottom nav collision", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 390,
    });

    render(
      <Providers>
        <span>Content</span>
      </Providers>
    );

    const toaster = screen.getByTestId("mock-toaster");
    expect(toaster).toHaveAttribute("data-position", "top-center");
  });

  it("dynamically switches Toaster position on window resize", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1024,
    });

    render(
      <Providers>
        <span>Content</span>
      </Providers>
    );

    let toaster = screen.getByTestId("mock-toaster");
    expect(toaster).toHaveAttribute("data-position", "bottom-right");

    // Simulate resizing to mobile width
    act(() => {
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        configurable: true,
        value: 480,
      });
      window.dispatchEvent(new Event("resize"));
    });

    toaster = screen.getByTestId("mock-toaster");
    expect(toaster).toHaveAttribute("data-position", "top-center");

    // Simulate resizing back to desktop width
    act(() => {
      Object.defineProperty(window, "innerWidth", {
        writable: true,
        configurable: true,
        value: 800,
      });
      window.dispatchEvent(new Event("resize"));
    });

    toaster = screen.getByTestId("mock-toaster");
    expect(toaster).toHaveAttribute("data-position", "bottom-right");
  });

  it("cleans up resize event listener on unmount", () => {
    const removeEventListenerSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = render(
      <Providers>
        <span>Content</span>
      </Providers>
    );

    unmount();

    expect(removeEventListenerSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    removeEventListenerSpy.mockRestore();
  });
});
