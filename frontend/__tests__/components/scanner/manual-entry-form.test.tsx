// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ManualEntryForm } from "@/components/scanner/manual-entry-form";
import * as apiClient from "@/lib/api/client";

// Mock the API client so no real network requests are made
vi.mock("@/lib/api/client", () => ({
  apiFetch: vi.fn(),
  apiClient: { get: vi.fn() },
}));

// Mock sonner toast so no real DOM notifications are triggered
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe("ManualEntryForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all form fields correctly with initial values", () => {
    const mockSubmit = vi.fn();
    const mockCancel = vi.fn();

    render(
      <ManualEntryForm
        onSubmit={mockSubmit}
        onCancel={mockCancel}
        initialIdentifier="9780131103627"
        initialFormat="book"
      />
    );

    expect(screen.getByText("Manual Item Entry")).toBeInTheDocument();
    expect(screen.getByDisplayValue("9780131103627")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Book (Generic)")).toBeInTheDocument();
  });

  it("handles form submission with correct data", async () => {
    const mockSubmit = vi.fn().mockResolvedValue(undefined);
    const mockCancel = vi.fn();

    render(<ManualEntryForm onSubmit={mockSubmit} onCancel={mockCancel} />);

    // Fill required field
    fireEvent.change(screen.getByLabelText(/Title \*/i), {
      target: { value: "The C Programming Language" },
    });

    // Fill optional fields
    fireEvent.change(screen.getByLabelText(/Creator\(s\)/i), {
      target: { value: "Brian W. Kernighan, Dennis M. Ritchie" },
    });
    fireEvent.change(screen.getByLabelText(/Publisher/i), {
      target: { value: "Prentice Hall" },
    });

    const submitBtn = screen.getByRole("button", { name: /Save Manual Entry/i });
    expect(submitBtn).not.toBeDisabled();

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith({
        title: "The C Programming Language",
        authors: "Brian W. Kernighan, Dennis M. Ritchie",
        identifier: "",
        publisher: "Prentice Hall",
        year: "",
        format: "book",
        coverFile: null,
      });
    });
  });

  it("triggers onCancel when close button is clicked", () => {
    const mockSubmit = vi.fn();
    const mockCancel = vi.fn();

    render(<ManualEntryForm onSubmit={mockSubmit} onCancel={mockCancel} />);

    const cancelBtn = screen.getByRole("button", { name: /Close manual entry/i });
    fireEvent.click(cancelBtn);

    expect(mockCancel).toHaveBeenCalledOnce();
  });

  it("renders a cover file input for manual cover upload", () => {
    const mockSubmit = vi.fn();
    const mockCancel = vi.fn();

    render(<ManualEntryForm onSubmit={mockSubmit} onCancel={mockCancel} />);

    expect(screen.getByLabelText(/Manual Cover Upload/i)).toBeInTheDocument();
    const fileInput = document.querySelector('input[type="file"]');
    expect(fileInput).toBeInTheDocument();
    expect(fileInput).toHaveAttribute("accept", "image/*");
  });

  /**
   * Phase 4 (0.7.8) – UX Polish: Lookup Loading State
   *
   * Verifies that while a slow ISBN/barcode metadata lookup is in-flight:
   * - A spinner ("Searching...") button appears in the DOM
   * - The lookup button and identifier input are both disabled (preventing double-click)
   * - After the promise resolves, all controls re-enable
   */
  it("Phase 4: displays a loading state and prevents double clicks during metadata lookup", async () => {
    const user = userEvent.setup();

    // Intercept apiFetch to simulate a slow network response
    let resolveApi!: (value: unknown) => void;
    const slowPromise = new Promise(resolve => {
      resolveApi = resolve;
    });
    vi.mocked(apiClient.apiFetch).mockReturnValue(slowPromise as never);

    render(<ManualEntryForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    // Type an identifier to enable the Lookup button
    const identifierInput = screen.getByPlaceholderText(/9780261102385/i);
    await user.type(identifierInput, "9780141182803");

    const lookupButton = screen.getByRole("button", { name: /Look up metadata for identifier/i });

    // Click Lookup – this should fire handleLookup and set isLookingUp=true
    await user.click(lookupButton);

    // Assert Phase 4 UX: spinner text appears and controls are locked
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Look up metadata for identifier/i })).toBeDisabled();
    });
    expect(identifierInput).toBeDisabled();
    // The submit button must also be disabled during lookup
    expect(screen.getByRole("button", { name: /Save Manual Entry/i })).toBeDisabled();

    // Resolve the slow promise to simulate network response arriving
    act(() => {
      resolveApi({ title: "1984", authors: "George Orwell", year: "1949" });
    });

    // Assert that controls re-enable once the promise settles
    await waitFor(() => {
      expect(identifierInput).not.toBeDisabled();
    });
    expect(screen.getByRole("button", { name: /Look up metadata for identifier/i })).not.toBeDisabled();
  });
});
