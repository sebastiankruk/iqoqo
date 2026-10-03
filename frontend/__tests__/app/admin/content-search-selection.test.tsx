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
 * The admin content search must not select a record on the user's behalf.
 *
 * `searchFrbrEntities` is a `%substring%` match (`app/api/admin.py:714`), so a
 * half-typed query can legitimately return exactly one row that is not what the
 * custodian meant. The previous auto-select turned that into an editor for the
 * wrong record without any click.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { searchFrbrEntities } from "@/lib/api/admin";

// The page is a server component tree; drive the wrapper through the real module.
vi.mock("@/lib/api/admin", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/admin")>();
  return { ...actual, searchFrbrEntities: vi.fn() };
});

vi.mock("@/components/admin/frbr-editor", () => ({
  FrbrEditor: ({ manifestationId }: { manifestationId: number }) => (
    <div data-testid="frbr-editor">Editing {manifestationId}</div>
  ),
}));

vi.mock("@/lib/api/hooks", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks")>();
  return {
    ...actual,
    useProfile: () => ({ data: { permissions: ["write:metadata"] }, isLoading: false }),
  };
});

const searchMock = vi.mocked(searchFrbrEntities);

/**
 * Import after the mocks are registered.
 *
 * @returns The page module's default export.
 */
async function loadPage() {
  const mod = await import("@/app/admin/content/page");
  return mod.default;
}

beforeEach(() => {
  searchMock.mockReset();
});

/**
 * Render the page inside the query provider its hooks require.
 *
 * @returns The testing-library render result.
 */
async function renderPage() {
  const Page = await loadPage();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <Page />
    </QueryClientProvider>
  );
}

/**
 * Render the page, type a term and submit the search.
 *
 * @param term - Text to search for.
 */
async function search(term: string) {
  const user = userEvent.setup();
  await renderPage();
  await user.type(screen.getByPlaceholderText(/Enter ISBN-13/i), `${term}{Enter}`);
}

describe("admin content search selection", () => {
  it("does not open the editor when a search returns exactly one result", async () => {
    // The whole point: one hit is still a choice, not a confirmation.
    searchMock.mockResolvedValue([{ id: 42, title: "Dune", isbn13: "9780441013593", type: "manifestation" }]);

    await search("dun");

    await waitFor(() => expect(screen.getByText("Search Results")).toBeInTheDocument());
    expect(screen.queryByTestId("frbr-editor")).not.toBeInTheDocument();
  });

  it("opens the editor only after the row is clicked", async () => {
    searchMock.mockResolvedValue([{ id: 42, title: "Dune", isbn13: "9780441013593", type: "manifestation" }]);
    const user = userEvent.setup();

    await search("dune");
    await waitFor(() => expect(screen.getByText("Search Results")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /Dune/ }));
    expect(screen.getByTestId("frbr-editor")).toHaveTextContent("Editing 42");
  });

  it("exposes the results to keyboard users", async () => {
    // Selection is now always explicit, so the row is the only way in. A
    // div-onClick would strand a keyboard-only custodian.
    searchMock.mockResolvedValue([{ id: 42, title: "Dune", type: "manifestation" }]);
    const user = userEvent.setup();

    await search("dune");
    await waitFor(() => expect(screen.getByText("Search Results")).toBeInTheDocument());

    const row = screen.getByRole("button", { name: /Dune/ });
    row.focus();
    await user.keyboard("{Enter}");
    expect(screen.getByTestId("frbr-editor")).toHaveTextContent("Editing 42");
  });

  it("does not auto-select across multiple results either", async () => {
    searchMock.mockResolvedValue([
      { id: 1, title: "Dune", type: "manifestation" },
      { id: 2, title: "Dune Messiah", type: "manifestation" },
    ]);

    await search("dune");

    await waitFor(() => expect(screen.getByText("Search Results")).toBeInTheDocument());
    expect(screen.queryByTestId("frbr-editor")).not.toBeInTheDocument();
  });

  it("lets the custodian return to search and choose again", async () => {
    searchMock.mockResolvedValue([{ id: 42, title: "Dune", type: "manifestation" }]);
    const user = userEvent.setup();

    await search("dune");
    await waitFor(() => expect(screen.getByText("Search Results")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /Dune/ }));
    expect(screen.getByTestId("frbr-editor")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Close/i }));
    expect(screen.queryByTestId("frbr-editor")).not.toBeInTheDocument();
  });

  it("reports a failed search rather than silently showing nothing", async () => {
    searchMock.mockRejectedValue(new Error("Search unavailable"));

    await search("dune");

    await waitFor(() => expect(screen.getByText("Search unavailable")).toBeInTheDocument());
  });
});
