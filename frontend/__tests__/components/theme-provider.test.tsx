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

import { render } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { ThemeProvider } from "@/components/theme-provider";

describe("ThemeProvider", () => {
  const originalNodeEnv = process.env.NODE_ENV;
  let originalConsoleError: typeof console.error;

  beforeEach(() => {
    originalConsoleError = console.error;
  });

  afterEach(() => {
    console.error = originalConsoleError;
    process.env.NODE_ENV = originalNodeEnv;
    vi.restoreAllMocks();
  });

  it("renders children", () => {
    const { getByText } = render(
      <ThemeProvider>
        <div>child content</div>
      </ThemeProvider>
    );
    expect(getByText("child content")).toBeTruthy();
  });

  it("suppresses the known 'script tag' React warning in development", () => {
    process.env.NODE_ENV = "development";
    const spy = vi.fn();
    console.error = spy;

    const { unmount } = render(
      <ThemeProvider>
        <div>content</div>
      </ThemeProvider>
    );

    console.error("Encountered a script tag while rendering React component");
    expect(spy).not.toHaveBeenCalled();

    unmount();
  });

  it("does not suppress unrelated console.error messages", () => {
    process.env.NODE_ENV = "development";
    const spy = vi.fn();
    console.error = spy;

    render(
      <ThemeProvider>
        <div>content</div>
      </ThemeProvider>
    );

    console.error("Some other real error");
    expect(spy).toHaveBeenCalledWith("Some other real error");
  });

  it("restores the original console.error on unmount", () => {
    process.env.NODE_ENV = "development";
    const spy = vi.fn();
    console.error = spy;

    const { unmount } = render(
      <ThemeProvider>
        <div>content</div>
      </ThemeProvider>
    );

    // console.error was swapped out for the filtering wrapper.
    expect(console.error).not.toBe(spy);

    unmount();

    // Restored to whatever console.error was right before mount (our spy).
    expect(console.error).toBe(spy);
  });

  it("does not touch console.error in production", () => {
    process.env.NODE_ENV = "production";
    const spy = vi.fn();
    console.error = spy;

    render(
      <ThemeProvider>
        <div>content</div>
      </ThemeProvider>
    );

    expect(console.error).toBe(spy);
  });
});
