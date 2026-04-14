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
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FrbrEditor } from "@/components/admin/frbr-editor";
import * as adminApi from "@/lib/api/admin";

vi.mock("@/lib/api/admin");

describe("FrbrEditor Component", () => {
  const mockFrbrTree = {
    work: { id: 1, title: "Dune", meta: { original_language: "en" } },
    expression: { id: 2, work_id: 1, content_type: "text", language: "en", meta: {} },
    manifestation: {
      id: 3,
      expression_id: 2,
      isbn13: "9780441172719",
      upc: null,
      ean: null,
      publisher: "Ace Books",
      publication_date: "1965-01-01",
      meta: { pages: "412" },
    },
    items: [{ id: 10, status: "available", condition: "Like New", meta: {}, owner_id: "user-1" }],
  };

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(adminApi.getFrbrTree).mockResolvedValue(mockFrbrTree);
    vi.mocked(adminApi.updateFrbrEntity).mockResolvedValue({ id: 1 });
  });

  it("renders loading state initially", () => {
    render(<FrbrEditor manifestationId={3} />);
    expect(screen.queryByText("Work (F1)")).not.toBeInTheDocument();
  });

  it("loads and renders the FRBR tree tabs", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => {
      expect(screen.getByText("Work (F1)")).toBeInTheDocument();
      expect(screen.getByText("Expression (F2)")).toBeInTheDocument();
      expect(screen.getByText("Manifestation (F3)")).toBeInTheDocument();
      expect(screen.getByText(/Items \(F5\)/)).toBeInTheDocument();
    });
  });

  it("displays manifestation data in the form", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue("9780441172719")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Ace Books")).toBeInTheDocument();
    });
  });

  it("allows switching to the Work tab and displays correct data", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByText("Work (F1)")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Work (F1)"));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Dune")).toBeInTheDocument();
    });
  });

  it("allows switching to the Expression tab", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByText("Expression (F2)")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Expression (F2)"));

    await waitFor(() => {
      expect(screen.getByDisplayValue("text")).toBeInTheDocument();
      expect(screen.getByDisplayValue("en")).toBeInTheDocument();
    });
  });

  it("allows switching to the Items tab", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByText(/Items \(F5\)/)).toBeInTheDocument());

    fireEvent.click(screen.getByText(/Items \(F5\)/));

    await waitFor(() => {
      expect(screen.getByText(/Item #10/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Like New/));

    await waitFor(() => {
      expect(screen.getByDisplayValue("available")).toBeInTheDocument();
    });
  });

  it("submits updated manifestation data to the API", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByText("Manifestation (F3)")).toBeInTheDocument());

    const pubInput = screen.getByDisplayValue("Ace Books");
    fireEvent.change(pubInput, { target: { value: "Penguin" } });

    const saveButton = screen.getByRole("button", { name: /Save Manifestation/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(adminApi.updateFrbrEntity).toHaveBeenCalledWith(
        "manifestation",
        3,
        expect.objectContaining({
          publisher: "Penguin",
          isbn13: "9780441172719",
        })
      );
    });
  });
});
