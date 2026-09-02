// Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

import { render, screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { DisambiguationSheet } from "@/components/scanner/disambiguation-sheet";
import type { IsbnMeta } from "@/types/frbr";

describe("DisambiguationSheet Component", () => {
  const mockCandidates: IsbnMeta[] = [
    {
      manifestation_id: 1,
      title: "The Hobbit",
      authors: ["J.R.R. Tolkien"],
      format: "book",
      cover_url: "/hobbit.png",
      already_in_collection: true,
    } as never,
    {
      manifestation_id: 2,
      title: "Dune",
      authors: ["Frank Herbert"],
      format: "book",
      cover_url: "",
      already_in_collection: false,
    } as never,
  ];

  it("renders multiple candidates correctly", () => {
    const mockSelect = vi.fn();
    const mockDismiss = vi.fn();

    render(<DisambiguationSheet candidates={mockCandidates} onSelect={mockSelect} onDismiss={mockDismiss} />);

    expect(screen.getByText("Which one did you mean?")).toBeInTheDocument();
    expect(screen.getByText("The Hobbit")).toBeInTheDocument();
    expect(screen.getByText("Dune")).toBeInTheDocument();
    expect(screen.getByText("In Collection")).toBeInTheDocument();
  });

  it("calls onSelect when a candidate is clicked", () => {
    const mockSelect = vi.fn();
    const mockDismiss = vi.fn();

    render(<DisambiguationSheet candidates={mockCandidates} onSelect={mockSelect} onDismiss={mockDismiss} />);

    fireEvent.click(screen.getByText("The Hobbit"));
    expect(mockSelect).toHaveBeenCalledWith(mockCandidates[0]);
  });

  it("calls onDismiss when cross icon button is clicked", () => {
    const mockSelect = vi.fn();
    const mockDismiss = vi.fn();

    render(<DisambiguationSheet candidates={mockCandidates} onSelect={mockSelect} onDismiss={mockDismiss} />);

    const closeBtn = screen.getByLabelText("Close");
    fireEvent.click(closeBtn);
    expect(mockDismiss).toHaveBeenCalledOnce();
  });
});
