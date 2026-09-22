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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ContributorEditor } from "@/components/admin/frbr/contributor-editor";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/hooks", () => ({
  useUserSearch: vi.fn(() => ({
    data: [],
    isLoading: false,
  })),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({ data: { success: true } }),
    delete: vi.fn().mockResolvedValue({ data: { success: true } }),
  },
}));

const mockContributors = [
  { id: 1, entity_type: "work", entity_id: 1, contributor_name: "Frank Herbert", role: "author" },
  { id: 2, entity_type: "work", entity_id: 1, contributor_name: "John Doe", role: "editor" },
];

describe("ContributorEditor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the Contributors heading", () => {
    render(<ContributorEditor entityType="work" entityId={1} />);
    expect(screen.getByText("Contributors")).toBeInTheDocument();
  });

  it("renders the search input", () => {
    render(<ContributorEditor entityType="work" entityId={1} />);
    expect(screen.getByPlaceholderText("Search contributors...")).toBeInTheDocument();
  });

  it("renders the role select with work roles", () => {
    render(<ContributorEditor entityType="work" entityId={1} />);
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "author" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "editor" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "translator" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "illustrator" })).toBeInTheDocument();
  });

  it("renders expression roles for expression entity type", () => {
    render(<ContributorEditor entityType="expression" entityId={2} />);
    expect(screen.getByRole("option", { name: "performer" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "director" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "conductor" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "narrator" })).toBeInTheDocument();
  });

  it("renders manifestation roles for manifestation entity type", () => {
    render(<ContributorEditor entityType="manifestation" entityId={3} />);
    expect(screen.getByRole("option", { name: "publisher" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "printer" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "distributor" })).toBeInTheDocument();
  });

  it("renders existing contributors", () => {
    render(<ContributorEditor entityType="work" entityId={1} contributors={mockContributors} />);
    expect(screen.getByText(/Frank Herbert/)).toBeInTheDocument();
    // Use getAllByText since "(author)" appears both in contributor list and role dropdown
    const authorMatches = screen.getAllByText(/(author)/);
    expect(authorMatches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/John Doe/)).toBeInTheDocument();
    const editorMatches = screen.getAllByText(/(editor)/);
    expect(editorMatches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders remove buttons for each contributor", () => {
    render(<ContributorEditor entityType="work" entityId={1} contributors={mockContributors} />);
    const removeButtons = screen.getAllByRole("button").filter(btn =>
      btn.querySelector("svg") !== null
    );
    expect(removeButtons.length).toBeGreaterThanOrEqual(2);
  });

  it("calls API to remove a contributor when remove button is clicked", async () => {
    render(<ContributorEditor entityType="work" entityId={1} contributors={mockContributors} />);
    const removeButtons = screen.getAllByRole("button").filter(btn =>
      btn.querySelector("svg") !== null
    );
    fireEvent.click(removeButtons[0]);
    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith("/v1/admin/frbr/contributions/1");
    });
  });

  it("calls onChanged callback after successful removal", async () => {
    const onChanged = vi.fn();
    render(
      <ContributorEditor entityType="work" entityId={1} contributors={mockContributors} onChanged={onChanged} />
    );
    const removeButtons = screen.getAllByRole("button").filter(btn =>
      btn.querySelector("svg") !== null
    );
    fireEvent.click(removeButtons[0]);
    await waitFor(() => {
      expect(onChanged).toHaveBeenCalled();
    });
  });

  it("handles remove error gracefully", async () => {
    vi.mocked(apiClient.delete).mockRejectedValueOnce(new Error("Network error"));
    render(<ContributorEditor entityType="work" entityId={1} contributors={mockContributors} />);
    const removeButtons = screen.getAllByRole("button").filter(btn =>
      btn.querySelector("svg") !== null
    );
    fireEvent.click(removeButtons[0]);
    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalled();
    });
  });

  it("disables Add button when search query is empty", () => {
    render(<ContributorEditor entityType="work" entityId={1} />);
    const addButton = screen.getByRole("button", { name: /Add/i });
    expect(addButton).toBeDisabled();
  });

  it("enables Add button when search query is non-empty", () => {
    render(<ContributorEditor entityType="work" entityId={1} />);
    const input = screen.getByPlaceholderText("Search contributors...");
    fireEvent.change(input, { target: { value: "John" } });
    const addButton = screen.getByRole("button", { name: /Add/i });
    expect(addButton).not.toBeDisabled();
  });

  it("calls API to add a contributor with free-text name", async () => {
    render(<ContributorEditor entityType="work" entityId={1} />);
    const input = screen.getByPlaceholderText("Search contributors...");
    fireEvent.change(input, { target: { value: "New Author" } });
    const addButton = screen.getByRole("button", { name: /Add/i });
    fireEvent.click(addButton);
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/v1/admin/frbr/contributions", {
        entity_type: "work",
        entity_id: 1,
        contributor_name: "New Author",
        contributor_id: undefined,
        role: "author",
      });
    });
  });

  it("calls onChanged callback after successful addition", async () => {
    const onChanged = vi.fn();
    render(<ContributorEditor entityType="work" entityId={1} onChanged={onChanged} />);
    const input = screen.getByPlaceholderText("Search contributors...");
    fireEvent.change(input, { target: { value: "New Author" } });
    fireEvent.click(screen.getByRole("button", { name: /Add/i }));
    await waitFor(() => {
      expect(onChanged).toHaveBeenCalled();
    });
  });

  it("handles add error gracefully", async () => {
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error("Server error"));
    render(<ContributorEditor entityType="work" entityId={1} />);
    const input = screen.getByPlaceholderText("Search contributors...");
    fireEvent.change(input, { target: { value: "New Author" } });
    fireEvent.click(screen.getByRole("button", { name: /Add/i }));
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalled();
    });
  });

  it("allows changing the selected role", () => {
    render(<ContributorEditor entityType="work" entityId={1} />);
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "translator" } });
    expect(select).toHaveValue("translator");
  });

  it("renders with empty contributors array by default", () => {
    render(<ContributorEditor entityType="work" entityId={1} />);
    // No contributor entries should be rendered (only role dropdown has "author")
    const removeButtons = screen.getAllByRole("button").filter(btn =>
      btn.querySelector("svg.text-destructive") !== null
    );
    expect(removeButtons.length).toBe(0);
  });

  it("shows search results when available", async () => {
    const { useUserSearch } = await import("@/lib/api/hooks");
    vi.mocked(useUserSearch).mockReturnValue({
      data: [
        { id: "user1", display_name: "Alice Smith", email: "alice@example.com" },
        { id: "user2", display_name: null, email: "bob@example.com" },
      ],
      isLoading: false,
    } as any);

    render(<ContributorEditor entityType="work" entityId={1} />);
    const input = screen.getByPlaceholderText("Search contributors...");
    fireEvent.change(input, { target: { value: "ali" } });

    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
      expect(screen.getByText("bob@example.com")).toBeInTheDocument();
    });
  });

  it("adds contributor from search results on click", async () => {
    const { useUserSearch } = await import("@/lib/api/hooks");
    vi.mocked(useUserSearch).mockReturnValue({
      data: [{ id: "user1", display_name: "Alice Smith", email: "alice@example.com" }],
      isLoading: false,
    } as any);

    render(<ContributorEditor entityType="work" entityId={1} />);
    const input = screen.getByPlaceholderText("Search contributors...");
    fireEvent.change(input, { target: { value: "ali" } });

    await waitFor(() => {
      expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Alice Smith"));
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/v1/admin/frbr/contributions", {
        entity_type: "work",
        entity_id: 1,
        contributor_name: "Alice Smith",
        contributor_id: "user1",
        role: "author",
      });
    });
  });

  it("falls back to contributor role for unknown entity types", () => {
    render(<ContributorEditor entityType={"unknown" as any} entityId={1} />);
    const select = screen.getByRole("combobox");
    expect(screen.getByRole("option", { name: "contributor" })).toBeInTheDocument();
    expect(select).toHaveValue("contributor");
  });
});
