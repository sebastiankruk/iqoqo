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
import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TaxonomyEditor } from "@/components/item/taxonomy-editor";
import type { Item } from "@/types/frbr";

const mockMutate = vi.fn();

vi.mock("@/lib/api/hooks", () => ({
  useUpdateItem: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe("TaxonomyEditor Physical Location & Tag Promotion (C157)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const baseItem = {
    id: 42,
    manifestation_id: 10,
    owner_id: "u1",
    status: "read",
    collection_status: "available",
    physical_location: "Study / Shelf 1",
    tags: ["loc:Living Room", "sci-fi"],
    meta: {},
  } as unknown as Item;

  it("updates, clears, and promotes non-empty folksonomy tags to physical_location", async () => {
    const user = userEvent.setup();
    render(<TaxonomyEditor item={{ ...baseItem, tags: ["loc:Living Room", "loc:   ", "sci-fi"] }} />);

    const locInput = screen.getByLabelText("Physical Location") as HTMLInputElement;
    expect(locInput.value).toBe("Study / Shelf 1");

    await user.clear(locInput);
    await user.type(locInput, "Bedroom / Shelf 3");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(mockMutate).toHaveBeenCalledWith({ physical_location: "Bedroom / Shelf 3" }, expect.any(Object));

    // Clearing saves physical_location: null
    await user.clear(locInput);
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(mockMutate).toHaveBeenCalledWith({ physical_location: null }, expect.any(Object));

    // Promote "loc:Living Room" tag to structured physical_location
    await user.click(screen.getByRole("button", { name: "Move loc:Living Room to Physical Location" }));
    expect(mockMutate).toHaveBeenCalledWith(
      { physical_location: "Living Room", tags: ["loc:   ", "sci-fi"] },
      expect.any(Object)
    );

    // Guard blank "loc:   " tag promotion (no-op)
    const callCountBefore = mockMutate.mock.calls.length;
    await user.click(screen.getByRole("button", { name: "Move loc: to Physical Location" }));
    expect(mockMutate).toHaveBeenCalledTimes(callCountBefore);
  });
});
