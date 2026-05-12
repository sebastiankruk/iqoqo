// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { ManualEntryForm } from "@/components/scanner/manual-entry-form";

describe("ManualEntryForm", () => {
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
});
