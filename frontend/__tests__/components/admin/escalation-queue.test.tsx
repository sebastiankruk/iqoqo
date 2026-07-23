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

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EscalationQueue } from "@/components/admin/escalation-queue";

vi.mock("@/lib/api/escalations", () => ({
  useEscalationQueue: vi.fn(),
  useResolveEscalation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

import * as escalationHooks from "@/lib/api/escalations";
import type { EscalationRequest } from "@/types/frbr";

const mockPendingRequest: EscalationRequest = {
  id: 1,
  user_id: "uuid-1",
  user_display_name: "Test User",
  user_username: "testuser",
  manifestation_id: 42,
  field_name: "title",
  suggested_value: "Correct Title",
  current_value: "Wrong Title",
  note: "Please fix",
  status: "pending",
  created_at: "2026-07-23T10:00:00Z",
  updated_at: "2026-07-23T10:00:00Z",
};

describe("EscalationQueue Component", () => {
  it("renders loading state", () => {
    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);
    expect(screen.getByTestId("escalation-queue-loading")).toBeInTheDocument();
  });

  it("renders empty state when no requests", () => {
    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);
    expect(screen.getByTestId("escalation-queue-empty")).toBeInTheDocument();
    expect(screen.getByText(/No pending escalation requests/i)).toBeInTheDocument();
  });

  it("renders pending requests with resolve buttons", () => {
    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [mockPendingRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);

    // Check the component renders
    expect(screen.getByTestId("escalation-queue")).toBeInTheDocument();

    // Check requester name
    expect(screen.getByText("Test User")).toBeInTheDocument();

    // Check target
    expect(screen.getByText(/Manifestation #42/i)).toBeInTheDocument();

    // Check field and value
    expect(screen.getByText("title")).toBeInTheDocument();
    expect(screen.getByText("Correct Title")).toBeInTheDocument();

    // Check note
    expect(screen.getByText("Please fix")).toBeInTheDocument();

    // Resolve buttons should be present
    expect(screen.getByText("Accept")).toBeInTheDocument();
    expect(screen.getByText("Reject")).toBeInTheDocument();
    expect(screen.getByText("Duplicate")).toBeInTheDocument();
  });

  it("renders requests with work, expression, and item targets", () => {
    const workRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 2,
      manifestation_id: undefined,
      work_id: 10,
    };

    const exprRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 3,
      manifestation_id: undefined,
      expression_id: 20,
    };

    const itemRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 4,
      manifestation_id: undefined,
      item_id: 30,
    };

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [workRequest, exprRequest, itemRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);

    expect(screen.getByText(/Work #10/i)).toBeInTheDocument();
    expect(screen.getByText(/Expression #20/i)).toBeInTheDocument();
    expect(screen.getByText(/Item #30/i)).toBeInTheDocument();
  });
});
