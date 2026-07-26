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
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FrbrEditor } from "@/components/admin/frbr-editor";
import * as adminApi from "@/lib/api/admin";
import { PermissionName } from "@/lib/permissions";

vi.mock("@/lib/api/admin");

vi.mock("@/lib/api/escalations", () => ({
  useCreateEscalation: vi.fn(() => ({
    mutateAsync: vi.fn(),
  })),
}));

vi.mock("@/lib/api/hooks", () => ({
  useWorkParts: vi.fn(() => ({
    data: { data: [] },
    isLoading: false,
    refetch: vi.fn(),
  })),
  useProfile: vi.fn(() => ({
    data: { permissions: [PermissionName.WRITE_METADATA, PermissionName.ESCALATE_REQUEST] },
  })),
}));

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
    vi.mocked(adminApi.getFrbrTree).mockImplementationOnce(() => new Promise(() => {}));
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

    await act(async () => {
      fireEvent.click(screen.getByText("Work (F1)"));
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Dune")).toBeInTheDocument();
    });
  });

  it("allows switching to the Expression tab", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByText("Expression (F2)")).toBeInTheDocument());

    await act(async () => {
      fireEvent.click(screen.getByText("Expression (F2)"));
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("Text (Book/Comic/Manga/Magazine)")).toBeInTheDocument();
      expect(screen.getByDisplayValue("en")).toBeInTheDocument();
    });
  });

  it("allows switching to the Items tab", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByText(/Items \(F5\)/)).toBeInTheDocument());

    await act(async () => {
      fireEvent.click(screen.getByText(/Items \(F5\)/));
    });

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

  it("submits updated manifestation type to the API", async () => {
    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByText("Manifestation (F3)")).toBeInTheDocument());

    const typeSelect = screen.getByDisplayValue("Book");
    fireEvent.change(typeSelect, { target: { value: "Movie" } });

    const saveButton = screen.getByRole("button", { name: /Save Manifestation/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(adminApi.updateFrbrEntity).toHaveBeenCalledWith(
        "manifestation",
        3,
        expect.objectContaining({
          meta: expect.objectContaining({
            type: "Movie",
          }),
        })
      );
    });
  });

  it("dispatches a User Request when changing type without WRITE_METADATA", async () => {
    // Override useProfile mock for this test only
    const { useProfile } = await import("@/lib/api/hooks");
    vi.mocked(useProfile).mockReturnValue({
      data: { permissions: [PermissionName.ESCALATE_REQUEST] }, // No WRITE_METADATA
    } as any);

    // Get the createEscalation mock
    const { useCreateEscalation } = await import("@/lib/api/escalations");
    const mutateAsyncMock = vi.fn();
    vi.mocked(useCreateEscalation).mockReturnValue({ mutateAsync: mutateAsyncMock } as any);

    render(<FrbrEditor manifestationId={3} />);

    await waitFor(() => expect(screen.getByText("Manifestation (F3)")).toBeInTheDocument());

    const typeSelect = screen.getByDisplayValue("Book");
    fireEvent.change(typeSelect, { target: { value: "Movie" } });

    const saveButton = screen.getByRole("button", { name: /Save Manifestation/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith(
        expect.objectContaining({
          level: "manifestation",
          targetId: 3,
          data: expect.objectContaining({
            request_type: "CHANGE_TYPE",
            field_name: "type",
            suggested_value: "Movie",
          }),
        })
      );
      // Ensure it doesn't call direct update
      expect(adminApi.updateFrbrEntity).not.toHaveBeenCalled();
    });
  });
});
