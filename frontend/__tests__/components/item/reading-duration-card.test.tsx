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

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReadingDurationCard } from "@/components/item/reading-duration-card";
import type { Item } from "@/types/frbr";

const mockMutate = vi.fn();

vi.mock("@/lib/api/hooks", () => ({
  useLogReadingSession: vi.fn(() => ({
    mutate: mockMutate,
    isPending: false,
  })),
}));

/**
 * Build a mock Item fixture for ReadingDurationCard tests.
 *
 * @param overrides - Partial Item field overrides
 * @returns Complete Item fixture
 */
function makeItem(overrides: Partial<Item> = {}): Item {
  return {
    id: 10,
    manifestation_id: 100,
    owner_id: "user-1",
    is_owner: true,
    status: "read",
    collection_status: "available",
    meta: {},
    reading_duration_summary: {
      total_minutes: 120,
      sessions_count: 3,
      started_at: "2026-11-01T10:00:00+00:00",
      finished_at: "2026-11-06T10:00:00+00:00",
      elapsed_days: 5,
    },
    ...overrides,
  };
}

describe("ReadingDurationCard", () => {
  beforeEach(() => {
    mockMutate.mockReset();
  });

  it("renders summary with hours, sessions, and elapsed days for owner", () => {
    render(<ReadingDurationCard item={makeItem()} isOwner={true} />);
    expect(screen.getByText(/2h 0m read across 3 sessions \(5 days\)/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Log Reading Time/i })).toBeInTheDocument();
  });

  it("does not render for non-owners", () => {
    const { container } = render(<ReadingDurationCard item={makeItem({ is_owner: false })} isOwner={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("submits quick preset (+30m) and custom session payload", () => {
    render(<ReadingDurationCard item={makeItem({ status: "reading" })} isOwner={true} />);

    fireEvent.click(screen.getByRole("button", { name: /Log Reading Time/i }));
    fireEvent.click(screen.getByRole("button", { name: "+30m" }));
    expect(mockMutate).toHaveBeenCalledWith({ duration_minutes: 30 }, expect.any(Object));

    fireEvent.change(screen.getByLabelText(/Minutes read/i), { target: { value: "45" } });
    fireEvent.change(screen.getByLabelText(/Pages read/i), { target: { value: "28" } });
    fireEvent.change(screen.getByLabelText(/Note/i), { target: { value: "Great chapter" } });
    fireEvent.click(screen.getByRole("button", { name: /Save Session/i }));

    expect(mockMutate).toHaveBeenCalledWith(
      { duration_minutes: 45, pages_read: 28, note: "Great chapter" },
      expect.any(Object)
    );
  });
});
