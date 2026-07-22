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

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("@/lib/api/escalations", () => ({
  useCreateEscalation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useMyEscalations: vi.fn(),
}));

import { useProfile } from "@/lib/api/hooks";
import { useMyEscalations } from "@/lib/api/escalations";
import { EscalationTrigger } from "@/components/escalation/escalation-trigger";

const mockUseProfile = vi.mocked(useProfile);
const mockUseMyEscalations = vi.mocked(useMyEscalations);

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
    expect(screen.getByText(/Escalation: pending/i)).toBeInTheDocument();
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

    expect(screen.getByText(/Escalation: accepted/i)).toBeInTheDocument();
    expect(screen.getByText(/Updated ISBN in metadata editor/i)).toBeInTheDocument();
  });
});
