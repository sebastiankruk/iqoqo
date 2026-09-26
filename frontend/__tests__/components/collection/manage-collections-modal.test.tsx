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
import { act, render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ManageCollectionsModal } from "@/components/collection/manage-collections-modal";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/lib/api/client";
import { toast } from "sonner";

// Mock apiClient
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    post: vi.fn(),
  },
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

describe("ManageCollectionsModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(apiClient.get).mockImplementation((url: string) => {
      if (url === "/collections") {
        return Promise.resolve({
          data: {
            success: true,
            collections: [
              { id: 1, name: "Fantasy", parent_id: null },
              { id: 2, name: "Sci-Fi", parent_id: null },
            ],
          },
        });
      }
      return Promise.resolve({ data: { success: true } });
    });
  });

  const renderComponent = (isOpen = true) =>
    render(
      <QueryClientProvider client={queryClient}>
        <ManageCollectionsModal isOpen={isOpen} onClose={vi.fn()} />
      </QueryClientProvider>
    );

  it("renders collections from the API", async () => {
    renderComponent();

    const dialog = await screen.findByRole("dialog", { name: "Manage Collections" });
    expect(dialog).toHaveClass("max-h-[calc(100dvh-2rem)]");
    expect(screen.getByRole("textbox", { name: "New collection name" })).toBeInTheDocument();
    expect(await screen.findByText("Fantasy")).toBeInTheDocument();
    expect(await screen.findByText("Sci-Fi")).toBeInTheDocument();
  });

  it("enters edit mode and allows renaming", async () => {
    renderComponent();

    const editButtons = await screen.findAllByTitle("Edit Name");
    expect(editButtons[0]).toHaveAccessibleName("Edit collection Fantasy");
    fireEvent.click(editButtons[0]);

    const editInput = screen.getByRole("textbox", { name: "Rename collection Fantasy" });
    fireEvent.change(editInput, { target: { value: "High Fantasy" } });

    vi.mocked(apiClient.put).mockResolvedValueOnce({ data: { success: true } });

    const saveButton = screen.getByText("Save");
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith("/collections/1", { name: "High Fantasy" });
    });
  });

  it("triggers deletion upon confirmation", async () => {
    renderComponent();

    const deleteButtons = await screen.findAllByTitle("Delete Collection");
    expect(deleteButtons[0]).toHaveAccessibleName("Delete collection Fantasy");

    vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: { success: true } });

    fireEvent.click(deleteButtons[0]);

    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent('Delete collection "Fantasy"?');
    expect(apiClient.delete).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm collection deletion" }));

    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith("/collections/1");
    });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
  });

  it("keeps the selected collection and dialog available after a failed delete", async () => {
    let rejectDelete: ((reason: Error) => void) | undefined;
    const failedAttempt = new Promise((_resolve, reject) => {
      rejectDelete = reject;
    });
    vi.mocked(apiClient.delete)
      .mockReturnValueOnce(failedAttempt as never)
      .mockResolvedValueOnce({ data: { success: true } });

    renderComponent();
    fireEvent.click(await screen.findByRole("button", { name: "Delete collection Fantasy" }));
    const dialog = await screen.findByRole("alertdialog");
    const confirmButton = screen.getByRole("button", { name: "Confirm collection deletion" });
    fireEvent.click(confirmButton);

    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
      expect(confirmButton).toBeDisabled();
    });

    await act(async () => {
      rejectDelete?.(new Error("Collection could not be removed"));
      await failedAttempt.catch(() => undefined);
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("Collection could not be removed");
    expect(toast.error).toHaveBeenCalledWith("Collection could not be removed");
    expect(screen.getByRole("alertdialog")).toBe(dialog);
    expect(screen.getByRole("button", { name: "Confirm collection deletion" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm collection deletion" }));

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(apiClient.delete).toHaveBeenCalledTimes(2);
  });

  it("does not delete a collection when confirmation is canceled", async () => {
    renderComponent();
    fireEvent.click((await screen.findAllByTitle("Delete Collection"))[0]);
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(apiClient.delete).not.toHaveBeenCalled();
  });

  it("allows keyboard dismissal of the deletion confirmation without deleting", async () => {
    renderComponent();
    fireEvent.click(await screen.findByRole("button", { name: "Delete collection Fantasy" }));

    const dialog = await screen.findByRole("alertdialog");
    fireEvent.keyDown(dialog, { key: "Escape" });

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(apiClient.delete).not.toHaveBeenCalled();
  });

  it("creates a new collection via the form", async () => {
    renderComponent();

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, collection: { id: 3, name: "History" } },
    });

    const input = screen.getByRole("textbox", { name: "New collection name" });
    fireEvent.change(input, { target: { value: "History" } });

    const addButton = screen.getByText("Add");
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/collections", {
        name: "History",
      });
    });
  });

  it("does not create a collection with empty name", () => {
    renderComponent();

    const addButton = screen.getByText("Add");
    expect(addButton).toBeDisabled();
  });

  it("clears input after successful creation", async () => {
    renderComponent();

    vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: { success: true, collection: { id: 4, name: "Poetry" } },
    });

    const input = screen.getByRole("textbox", { name: "New collection name" });
    fireEvent.change(input, { target: { value: "Poetry" } });
    fireEvent.click(screen.getByText("Add"));

    await waitFor(() => {
      expect(input).toHaveValue("");
    });
  });
});
