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
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EscalationQueue } from "@/components/admin/escalation-queue";

// Mock next-intl to provide translations for HelpRequests namespace
vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: (namespace: string) => {
    if (namespace === "HelpRequests") {
      return (key: string, values?: Record<string, string | number>) => {
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
          acceptAndDelete: "Accept & Delete",
          deletePermissionRequired: "Delete permission required",
          correction: "Correction",
          deletion: "Deletion",
          reasonForDeletion: "Reason for deletion",
          resolvedBy: "Resolved by {name}",
          entityRemovedSuccess: "Entity removed successfully",
        };
        let result = translations[key] || key;
        if (values) {
          Object.entries(values).forEach(([k, v]) => {
            result = result.replace(`{${k}}`, String(v));
          });
        }
        return result;
      };
    }
    return (key: string) => key;
  },
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("@/lib/api/escalations", () => ({
  useEscalationQueue: vi.fn(),
  useResolvedEscalations: vi.fn(),
  useResolveEscalation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

import { useProfile } from "@/lib/api/hooks";
import * as escalationHooks from "@/lib/api/escalations";
import type { EscalationRequest } from "@/types/frbr";

/** Default resolved escalations mock for when toggle is closed (enabled=false) */
const defaultResolvedReturn = {
  data: undefined,
  isLoading: false,
  isError: false,
  error: null,
} as unknown as ReturnType<typeof escalationHooks.useResolvedEscalations>;

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
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useProfile).mockReturnValue({
      data: { permissions: ["delete:manifestation", "delete:item"] },
    } as unknown as ReturnType<typeof useProfile>);
  });
  beforeEach(() => {
    vi.mocked(useProfile).mockReturnValue({
      data: {
        permissions: ["delete:manifestation", "delete:item"],
      },
    } as unknown as ReturnType<typeof useProfile>);

    // Default for when toggle is closed
    vi.mocked(escalationHooks.useResolvedEscalations).mockReturnValue(defaultResolvedReturn);
  });

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

    expect(screen.getByTestId("escalation-queue")).toBeInTheDocument();
    expect(screen.getByText("Test User")).toBeInTheDocument();
    expect(screen.getByText(/Manifestation #42/i)).toBeInTheDocument();
    expect(screen.getByText("title")).toBeInTheDocument();
    expect(screen.getByText("Correct Title")).toBeInTheDocument();
    expect(screen.getByText("Please fix")).toBeInTheDocument();
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

  // ── 4.1 Error state ────────────────────────────────────────────────────
  it("renders error state when queue fetch fails", () => {
    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Network failure"),
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);
    expect(screen.getByText(/Failed to load escalation queue/i)).toBeInTheDocument();
    expect(screen.getByText(/Network failure/i)).toBeInTheDocument();
  });

  // ── 4.2 Processed requests toggle opens and fetches ────────────────────
  it("processed requests toggle opens and shows resolved data", async () => {
    const user = userEvent.setup();
    const resolvedRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 5,
      status: "accepted" as const,
      resolver_display_name: "Dr. Custodian",
      resolved_at: "2026-07-24T10:00:00Z",
    };

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [mockPendingRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    vi.mocked(escalationHooks.useResolvedEscalations).mockReturnValue({
      data: [resolvedRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useResolvedEscalations>);

    render(<EscalationQueue />);

    const toggle = screen.getByRole("button", { name: /Processed Requests/i });
    await user.click(toggle);

    // After clicking, resolved request with resolver display name should be visible
    expect(screen.getByText(/Dr\. Custodian/i)).toBeInTheDocument();
  });

  // ── 4.3 Processed requests loading state ───────────────────────────────
  it("processed requests section shows loading state", async () => {
    const user = userEvent.setup();

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [mockPendingRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    vi.mocked(escalationHooks.useResolvedEscalations).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useResolvedEscalations>);

    render(<EscalationQueue />);

    const toggle = screen.getByRole("button", { name: /Processed Requests/i });
    await user.click(toggle);

    // Loading skeleton should render animated pulse divs
    const loadingCards = document.querySelectorAll(".animate-pulse");
    expect(loadingCards.length).toBeGreaterThan(0);
  });

  // ── 4.4 Processed requests empty state ─────────────────────────────────
  it("processed requests section shows empty state", async () => {
    const user = userEvent.setup();

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [mockPendingRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    vi.mocked(escalationHooks.useResolvedEscalations).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useResolvedEscalations>);

    render(<EscalationQueue />);

    const toggle = screen.getByRole("button", { name: /Processed Requests/i });
    await user.click(toggle);

    expect(screen.getByText("No processed requests yet")).toBeInTheDocument();
  });

  // ── 4.5 Processed requests error state ─────────────────────────────────
  it("processed requests section shows error state", async () => {
    const user = userEvent.setup();

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [mockPendingRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    vi.mocked(escalationHooks.useResolvedEscalations).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Server error"),
    } as unknown as ReturnType<typeof escalationHooks.useResolvedEscalations>);

    render(<EscalationQueue />);

    const toggle = screen.getByRole("button", { name: /Processed Requests/i });
    await user.click(toggle);

    expect(screen.getByText(/Failed to load processed/i)).toBeInTheDocument();
  });

  // ── 4.6 Resolver display name visible ──────────────────────────────────
  it("resolved request card shows resolver display name", async () => {
    const user = userEvent.setup();
    const resolvedRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 10,
      status: "accepted" as const,
      resolver_display_name: "Dr. Custodian",
      resolved_at: "2026-07-24T10:00:00Z",
    };

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [mockPendingRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    vi.mocked(escalationHooks.useResolvedEscalations).mockReturnValue({
      data: [resolvedRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useResolvedEscalations>);

    render(<EscalationQueue />);

    const toggle = screen.getByRole("button", { name: /Processed Requests/i });
    await user.click(toggle);

    expect(screen.getByText(/Dr\. Custodian/i)).toBeInTheDocument();
  });

  // ── 4.7 Deletion request badge ─────────────────────────────────────────
  it("deletion request shows deletion badge distinct from correction", () => {
    const deletionRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 11,
      request_type: "deletion",
      field_name: "",
    };

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [deletionRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);

    // The deletion badge should be present with text-destructive styling
    expect(screen.getByText("Deletion")).toBeInTheDocument();
  });

  // ── 4.8 Deletion accept button gated on permission ─────────────────────
  it("deletion accept button is disabled without delete:manifestation permission", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { permissions: [] },
    } as unknown as ReturnType<typeof useProfile>);

    const deletionRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 12,
      request_type: "deletion",
      field_name: "",
    };

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [deletionRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);

    // The Accept & Delete button should be disabled
    const acceptButton = screen.getByText("Accept & Delete");
    expect(acceptButton).toBeDisabled();
    expect(acceptButton).toHaveAttribute("title", "Delete permission required");
  });

  // ── 4.9 Deletion accept for items requires DELETE_ITEM permission ──────
  it("deletion accept for item targets shows permission gating", () => {
    vi.mocked(useProfile).mockReturnValue({
      data: { permissions: ["delete:manifestation"] }, // has manifest delete but not item delete
    } as unknown as ReturnType<typeof useProfile>);

    const itemDeletionRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 13,
      manifestation_id: undefined,
      item_id: 30,
      request_type: "deletion",
      field_name: "",
    };

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [itemDeletionRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);

    // The item deletion accept button should be disabled (no delete:item permission)
    const acceptButton = screen.getByText("Accept & Delete");
    expect(acceptButton).toBeDisabled();
  });

  // ── 4.10 Clickable target label has correct href ────────────────────────
  it("clickable target label has correct href for manifestation", () => {
    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [mockPendingRequest], // manifestation_id: 42
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);

    // The target label should be a link to the admin editor
    const link = screen.getByText(/Manifestation #42/i);
    expect(link.closest("a")).toHaveAttribute("href", "/admin/content?tab=metadata&manifestationId=42");
  });

  it("renders RequestTypeBadge with 'Change Type' when request_type is change_type", () => {
    const changeTypeRequest: EscalationRequest = {
      ...mockPendingRequest,
      id: 15,
      request_type: "change_type",
      field_name: "type",
      suggested_value: "movie",
    };

    vi.mocked(escalationHooks.useEscalationQueue).mockReturnValue({
      data: [changeTypeRequest],
      isLoading: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof escalationHooks.useEscalationQueue>);

    render(<EscalationQueue />);

    expect(screen.getByText("Change Type")).toBeInTheDocument();
  });
});
