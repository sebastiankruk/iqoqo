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

// Mock next-intl to provide translations for HelpRequests namespace
vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: (namespace: string) => {
    if (namespace === "HelpRequests") {
      return (key: string) => {
        const translations: Record<string, string> = {
          accept: "Accept",
          accepted: "Accepted",
          rejected: "Rejected",
          duplicate: "Duplicate",
          pending: "Pending",
          reject: "Reject",
          confirm: "Confirm",
          cancel: "Cancel",
          markAsDuplicate: "Mark as Duplicate",
          noPendingUserRequests: "No pending user requests",
          newRequestsAppear: "New requests from users will appear here.",
          failedToLoad: "Failed to load escalation queue",
          failedToLoadProcessed: "Failed to load processed requests",
          resolutionNoteOptional: "Resolution note (optional)",
          processedRequests: "Processed Requests",
          noProcessedRequests: "No processed requests yet",
          requestAccepted: "Request accepted",
          requestRejected: "Request rejected",
          requestDuplicate: "Request marked as duplicate",
          failedToResolve: "Failed to resolve request",
        };
        return translations[key] || key;
      };
    }
    return (key: string) => key;
  },
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

vi.mock("@/lib/api/escalations", () => ({
  useEscalationQueue: vi.fn(),
  useResolvedEscalations: vi.fn(() => ({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
  })),
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
    expect(screen.getByText(/No pending user requests/i)).toBeInTheDocument();
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
    expect(screen.getByText("Mark as Duplicate")).toBeInTheDocument();
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
