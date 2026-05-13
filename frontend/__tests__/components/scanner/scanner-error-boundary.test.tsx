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
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScannerErrorBoundary } from "@/components/scanner/error-boundary";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// A component that throws an error to test the boundary
const ProblemChild = ({ shouldThrow = false }) => {
  if (shouldThrow) {
    throw new Error("Test Error: Scanner component crashed!");
  }
  return <div>Scanner Content</div>;
};

describe("ScannerErrorBoundary", () => {
  // Prevent console.error from polluting test output
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
    vi.spyOn(window.location, "reload").mockImplementation(() => {});
  });

  afterEach(() => {
    console.error = originalError;
  });

  it("renders children when there is no error", () => {
    render(
      <ScannerErrorBoundary>
        <ProblemChild />
      </ScannerErrorBoundary>
    );
    expect(screen.getByText("Scanner Content")).toBeDefined();
  });

  it("renders custom fallback when an error occurs", () => {
    render(
      <ScannerErrorBoundary fallback={<div>Custom Error UI</div>}>
        <ProblemChild shouldThrow={true} />
      </ScannerErrorBoundary>
    );
    expect(screen.getByText("Custom Error UI")).toBeDefined();
    expect(screen.queryByText("Scanner Content")).toBeNull();
  });

  it("renders default fallback with error message and reload button", () => {
    render(
      <ScannerErrorBoundary>
        <ProblemChild shouldThrow={true} />
      </ScannerErrorBoundary>
    );

    expect(screen.getByText("Something went wrong with the scanner")).toBeDefined();
    expect(screen.getByText("Test Error: Scanner component crashed!")).toBeDefined();
    expect(screen.getByRole("button", { name: /reload scanner/i })).toBeDefined();
  });

  it("reloads the page when 'Reload Scanner' is clicked", () => {
    render(
      <ScannerErrorBoundary>
        <ProblemChild shouldThrow={true} />
      </ScannerErrorBoundary>
    );

    const reloadButton = screen.getByRole("button", { name: /reload scanner/i });
    fireEvent.click(reloadButton);

    expect(window.location.reload).toHaveBeenCalled();
  });
});
