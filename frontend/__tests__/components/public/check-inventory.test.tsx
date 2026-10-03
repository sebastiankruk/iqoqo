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
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CheckInventory } from "@/components/public/check-inventory";
import { apiClient } from "@/lib/api/client";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("next/image", () => ({
  // A plain img keeps the assertion about rendering, not image optimisation.
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}));

const post = vi.spyOn(apiClient, "post");

/**
 * Render the component, type a query and submit it.
 *
 * @param query - Text to enter into the search field.
 */
async function submit(query: string) {
  const user = userEvent.setup();
  render(<CheckInventory username="jane" />);
  await user.type(screen.getByTestId("check-inventory-input"), query);
  await user.click(screen.getByRole("button"));
}

beforeEach(() => {
  post.mockReset();
});

describe("CheckInventory", () => {
  it("posts the trimmed query and renders a match", async () => {
    post.mockResolvedValue({
      data: {
        success: true,
        data: [{ type: "item", id: 7, manifestation_id: 42, title: "Dune", status: "owned" }],
      },
    });

    await submit("  Dune  ");

    await waitFor(() => expect(screen.getByText("Dune")).toBeInTheDocument());
    expect(post).toHaveBeenCalledWith("/public/u/jane/check", { query: "Dune" });
  });

  it("shows an empty-collection answer rather than treating it as a failure", async () => {
    // The backend returns `{success: true, data: []}` for a genuine miss.
    post.mockResolvedValue({ data: { success: true, data: [] } });

    await submit("Nothing Here");

    await waitFor(() => expect(screen.getByText("notFound")).toBeInTheDocument());
    expect(screen.getByText("notFound")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("surfaces a failed request instead of rendering nothing", async () => {
    // The previous raw-fetch version did `if (data.success) setResult(data)`,
    // so a 404 `{error: "User not found"}` produced an entirely blank panel --
    // indistinguishable from a miss.
    post.mockRejectedValue(new Error("User not found"));

    await submit("Anything");

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("alert")).toHaveTextContent("checkFailed");
    expect(screen.queryByTestId("inventory-result-card")).not.toBeInTheDocument();
  });

  it("treats a malformed 200 body as a failure", async () => {
    post.mockResolvedValue({ data: { success: true } });

    await submit("Anything");

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("clears a previous error when a later check succeeds", async () => {
    post.mockRejectedValueOnce(new Error("boom"));
    await submit("First");
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    post.mockResolvedValueOnce({ data: { success: true, data: [] } });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button"));

    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });

  it("does not call the API for an empty query", async () => {
    const user = userEvent.setup();
    render(<CheckInventory username="jane" />);
    await user.click(screen.getByRole("button"));
    expect(post).not.toHaveBeenCalled();
  });
});
