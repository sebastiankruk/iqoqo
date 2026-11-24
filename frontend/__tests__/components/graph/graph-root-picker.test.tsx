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
import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { GraphRootPicker } from "@/components/graph/graph-root-picker";

const mockUseCatalogGraphSearch = vi.fn();

vi.mock("@/lib/hooks/use-debounce", () => ({
  useDebounce: <T,>(value: T) => value,
}));

vi.mock("@/lib/api/hooks/catalog", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks/catalog")>();
  return {
    ...actual,
    useCatalogGraphSearch: (q: string, types?: string, limit?: number, enabled?: boolean) =>
      mockUseCatalogGraphSearch(q, types, limit, enabled),
  };
});

describe("GraphRootPicker (C143)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCatalogGraphSearch.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });
  });

  it("shows minimum-character guard when trimmed query has fewer than 2 characters", () => {
    const onSelect = vi.fn();
    render(<GraphRootPicker onSelect={onSelect} />);

    const input = screen.getByTestId("graph-picker-input");
    fireEvent.change(input, { target: { value: "L" } });

    expect(screen.getByTestId("graph-picker-min-chars")).toBeInTheDocument();
    expect(screen.queryByTestId("graph-picker-listbox")).not.toBeInTheDocument();
    expect(mockUseCatalogGraphSearch).toHaveBeenLastCalledWith("L", undefined, 10, false);
  });

  it("supports keyboard ArrowDown/Enter selection and Escape dismissal", async () => {
    const onSelect = vi.fn();
    mockUseCatalogGraphSearch.mockReturnValue({
      data: [
        {
          entity_type: "person",
          entity_id: 7,
          label: "Stanisław Lem",
          subtitle: "person",
          contributor_type: "person",
          url: "/collection?q=Stanis%C5%82aw+Lem",
        },
        {
          entity_type: "series",
          entity_id: 19,
          label: "Dune Chronicles",
          subtitle: "series",
          work_kind: "series",
          url: "/work/19",
        },
      ],
      isLoading: false,
      isError: false,
    });

    render(<GraphRootPicker onSelect={onSelect} />);
    const input = screen.getByTestId("graph-picker-input");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "Le" } });

    expect(screen.getByTestId("graph-picker-listbox")).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(onSelect).toHaveBeenCalledWith("person", 7);

    fireEvent.focus(input);
    expect(screen.getByTestId("graph-picker-listbox")).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByTestId("graph-picker-listbox")).not.toBeInTheDocument();
    });
  });

  it("renders localized error state when search API fails", () => {
    mockUseCatalogGraphSearch.mockReturnValue({
      data: [],
      isLoading: false,
      isError: true,
    });

    render(<GraphRootPicker onSelect={vi.fn()} />);
    const input = screen.getByTestId("graph-picker-input");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "Lem" } });

    expect(screen.getByTestId("graph-picker-error")).toBeInTheDocument();
  });
});
