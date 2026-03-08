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
 * Tests for the SuccessCard component.
 *
 * Simulates post-scan state: the card receives isbn + meta props, lets the
 * user dismiss the result or add the book to the library.
 *
 * Mocks:
 * - next/navigation (useRouter) – global in vitest.setup.ts
 * - sonner (toast) – global in vitest.setup.ts
 * - @/lib/api/client (apiClient.post) – per-test via the mock factory below
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SuccessCard } from "@/components/scanner/success-card";

describe("SuccessCard", () => {
  const defaultProps = {
    title: "Dune",
    message: "Successfully added to your library.",
    onViewItem: vi.fn(),
    onScanNext: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the success header and message", () => {
    render(<SuccessCard {...defaultProps} />);
    expect(screen.getByText("Successfully Added!")).toBeInTheDocument();
    expect(screen.getByText("Successfully added to your library.")).toBeInTheDocument();
  });

  it("renders the book title in quotes", () => {
    render(<SuccessCard {...defaultProps} />);
    expect(screen.getByText("Dune")).toBeInTheDocument();
  });

  it("calls onViewItem when 'View in Collection' is clicked", () => {
    render(<SuccessCard {...defaultProps} />);
    const viewBtn = screen.getByRole("button", { name: /view in collection/i });
    fireEvent.click(viewBtn);
    expect(defaultProps.onViewItem).toHaveBeenCalledOnce();
  });

  it("calls onScanNext when 'Scan Another' is clicked", () => {
    render(<SuccessCard {...defaultProps} />);
    const scanBtn = screen.getByRole("button", { name: /scan another/i });
    fireEvent.click(scanBtn);
    expect(defaultProps.onScanNext).toHaveBeenCalledOnce();
  });
});
