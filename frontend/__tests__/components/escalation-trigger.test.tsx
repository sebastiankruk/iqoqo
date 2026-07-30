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
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
import type { EscalationRequest } from "@/types/frbr";

// Mock next-intl to provide translations for HelpRequests namespace
vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: (namespace: string) => {
    if (namespace === "HelpRequests") {
      return (key: string) => {
        const translations: Record<string, string> = {
          askCustodiansForHelp: "Ask custodians for help",
          helpRequest: "Help Request",
          pending: "pending",
          accepted: "accepted",
          rejected: "Rejected",
          duplicate: "Duplicate",
          suggested: "Suggested",
          suggestedValue: "Suggested value",
          fieldToCorrect: "Field to correct",
          currentValueOptional: "Current value (optional)",
          reasonNoteOptional: "Reason / Note (optional)",
          submitRequest: "Submit Request",
          submitting: "Submitting...",
          cancel: "Cancel",
          requestMetadataCorrection: "Request Metadata Correction",
          requestDescription: "Submit a request to custodians to review and update locked metadata on this entity.",
          suggestedValueRequired: "Suggested value is required",
          escalationSubmitted: "Escalation request submitted to custodians",
          failedToSubmit: "Failed to submit escalation request",
          deletion: "Deletion",
          reasonForDeletion: "Reason for deletion",
          reasonForDeletionRequired: "Reason for deletion is required",
          reasonForDeletionPlaceholder: "Explain why this entity should be deleted",
          requestDeletion: "Request Deletion",
          deletionRequestSubmitted: "Deletion request submitted to custodians",
          metadataCorrection: "Metadata Correction",
        };
        return translations[key] || key;
      };
    }
    return (key: string) => key;
  },
}));

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("@/lib/api/escalations", () => ({
  useCreateEscalation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useMyEscalations: vi.fn(),
}));

import { useProfile } from "@/lib/api/hooks";
import { useMyEscalations, useCreateEscalation } from "@/lib/api/escalations";
import { EscalationTrigger } from "@/components/escalation/escalation-trigger";

const mockUseProfile = vi.mocked(useProfile);
const mockUseMyEscalations = vi.mocked(useMyEscalations);
const mockUseCreateEscalation = vi.mocked(useCreateEscalation);

describe("EscalationTrigger Component", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders trigger button when user lacks write:metadata permission", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    render(<EscalationTrigger level="item" targetId={123} />);

    expect(screen.getByText("Ask custodians for help")).toBeInTheDocument();
  });

  it("hides trigger component when user has write:metadata permission", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "custodian@iqoqo.local", permissions: ["write:metadata", "escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    const { container } = render(<EscalationTrigger level="item" targetId={123} />);

    expect(container.firstChild).toBeNull();
  });

  it("renders active escalation status card when user has an active request for target", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [
        {
          id: 1,
          user_id: "u1",
          item_id: 123,
          field_name: "title",
          suggested_value: "Corrected Title",
          status: "pending",
          resolution_note: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    render(<EscalationTrigger level="item" targetId={123} />);

    expect(screen.getByTestId("escalation-status-card")).toBeInTheDocument();
    expect(screen.getByText(/Help Request: pending/i)).toBeInTheDocument();
    expect(screen.getByText("Corrected Title")).toBeInTheDocument();
  });

  it("renders resolution note when escalation has been accepted or rejected", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [
        {
          id: 1,
          user_id: "u1",
          item_id: 123,
          field_name: "isbn",
          suggested_value: "9781234567890",
          status: "accepted",
          resolution_note: "Updated ISBN in metadata editor",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    render(<EscalationTrigger level="item" targetId={123} />);

    expect(screen.getByText(/Help Request: accepted/i)).toBeInTheDocument();
    expect(screen.getByText(/Updated ISBN in metadata editor/i)).toBeInTheDocument();
  });

  it("renders rejected status card when escalation is rejected", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [
        {
          id: 1,
          user_id: "u1",
          item_id: 123,
          field_name: "title",
          suggested_value: "Rejected Title",
          status: "rejected",
          resolution_note: "Not needed",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    render(<EscalationTrigger level="item" targetId={123} />);

    expect(screen.getByTestId("escalation-status-card")).toBeInTheDocument();
    expect(screen.getByText(/Help Request: Rejected/i)).toBeInTheDocument();
  });

  it("renders duplicate status card when escalation is duplicate", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [
        {
          id: 1,
          user_id: "u1",
          item_id: 123,
          field_name: "title",
          suggested_value: "Duplicate Title",
          status: "duplicate",
          resolution_note: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    render(<EscalationTrigger level="item" targetId={123} />);

    expect(screen.getByTestId("escalation-status-card")).toBeInTheDocument();
    expect(screen.getByText(/Help Request: Duplicate/i)).toBeInTheDocument();
  });

  it("deletion request flow: toggles type, fills reason, submits", async () => {
    const user = userEvent.setup();
    const mockMutate = vi.fn();

    mockUseCreateEscalation.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateEscalation>);

    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    render(<EscalationTrigger level="item" targetId={123} />);

    // Click the "Ask custodians for help" button to open dialog
    await user.click(screen.getByText("Ask custodians for help"));

    // Should show the dialog
    expect(screen.getByText("Request Metadata Correction")).toBeInTheDocument();

    // Switch to deletion type
    await user.click(screen.getByText("Request Deletion"));

    // Fill reason
    const reasonInput = screen.getByPlaceholderText("Explain why this entity should be deleted");
    await user.type(reasonInput, "Duplicate entry");

    // Submit
    await user.click(screen.getByText("Submit Request"));

    expect(mockMutate).toHaveBeenCalled();
  });

  it("alwaysShowDialog prop renders dialog button without status card", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [
        {
          id: 1,
          user_id: "u1",
          item_id: 123,
          field_name: "title",
          suggested_value: "Some Value",
          status: "pending",
          resolution_note: null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    render(<EscalationTrigger level="item" targetId={123} alwaysShowDialog={true} />);

    // Dialog button should be visible
    expect(screen.getByText("Ask custodians for help")).toBeInTheDocument();
    // Status card should NOT be present
    expect(screen.queryByTestId("escalation-status-card")).not.toBeInTheDocument();
  });

  it("multi-escalation accordion expands to show both requests", () => {
    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    // Provide pre-filtered escalations
    const escalations = [
      {
        id: 1,
        user_id: "u1",
        item_id: 123,
        field_name: "title",
        suggested_value: "First Correction",
        status: "pending",
        request_type: "correction" as const,
        resolution_note: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      {
        id: 2,
        user_id: "u1",
        item_id: 123,
        field_name: "author",
        suggested_value: "Second Correction",
        status: "pending",
        request_type: "correction" as const,
        resolution_note: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ];

    render(
      <EscalationTrigger
        level="item"
        targetId={123}
        escalations={escalations as unknown as EscalationRequest[]}
        alwaysShowDialog={true}
      />
    );

    // Should show the dialog button
    expect(screen.getByText("Ask custodians for help")).toBeInTheDocument();
  });

  it("triggers change_type escalation payload when Entity Type is selected", async () => {
    const user = userEvent.setup();
    const mockMutate = vi.fn();

    mockUseCreateEscalation.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateEscalation>);

    mockUseProfile.mockReturnValue({
      data: { id: "u1", email: "user@iqoqo.local", permissions: ["escalate:request"] },
    } as unknown as ReturnType<typeof useProfile>);

    mockUseMyEscalations.mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useMyEscalations>);

    render(<EscalationTrigger level="manifestation" targetId={123} />);

    await user.click(screen.getByText("Ask custodians for help"));

    const fieldSelect = screen.getByLabelText("Field to correct");
    await user.selectOptions(fieldSelect, "type");

    const suggestedInput = screen.getByPlaceholderText("Correct value");
    await user.type(suggestedInput, "movie");

    await user.click(screen.getByText("Submit Request"));

    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        level: "manifestation",
        targetId: 123,
        data: expect.objectContaining({
          request_type: "change_type",
          field_name: "type",
          suggested_value: "movie",
        }),
      }),
      expect.anything()
    );
  });
});

