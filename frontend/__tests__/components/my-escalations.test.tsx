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
import { describe, it, expect, vi } from "vitest";
import { MyEscalations } from "@/components/escalation/my-escalations";
import * as escalationsApi from "@/lib/api/escalations";

// Mock next-intl to provide translations for HelpRequests namespace
vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: (namespace: string) => {
    if (namespace === "HelpRequests") {
      return (key: string) => {
        const translations: Record<string, string> = {
          helpRequestsTitle: "Help Requests",
          helpRequestsDesc: "Metadata correction requests submitted to custodians",
          noHelpRequestsSubmitted: "No help requests submitted",
          helpRequestsHint:
            "When you request metadata corrections on item or manifestation pages, your requests will appear here.",
          trackStatusDesc: "Track status and custodian responses for your metadata correction requests",
          pending: "Pending",
          accepted: "Accepted",
          rejected: "Rejected",
          duplicate: "Duplicate",
          custodianNote: "Custodian note",
          deletion: "Deletion",
          correction: "Correction",
          reasonForDeletion: "Reason for deletion",
        };
        return translations[key] || key;
      };
    }
    return (key: string) => key;
  },
}));

vi.mock("@/lib/api/escalations", () => ({
  useMyEscalations: vi.fn(),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

describe("MyEscalations Component", () => {
  it("renders loading state", () => {
    vi.mocked(escalationsApi.useMyEscalations).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as unknown as ReturnType<typeof escalationsApi.useMyEscalations>);

    render(<MyEscalations />);
    expect(screen.getByText("Help Requests")).toBeInTheDocument();
  });

  it("renders empty state when user has no submitted requests", () => {
    vi.mocked(escalationsApi.useMyEscalations).mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof escalationsApi.useMyEscalations>);

    render(<MyEscalations />);
    expect(screen.getByText("No help requests submitted")).toBeInTheDocument();
  });

  it("renders submitted escalation requests with status and details", () => {
    vi.mocked(escalationsApi.useMyEscalations).mockReturnValue({
      data: [
        {
          id: 1,
          user_id: "user-1",
          manifestation_id: 2007,
          field_name: "author",
          current_value: undefined,
          suggested_value: "Alice Vincent",
          note: "Missing author metadata",
          status: "pending",
          resolution_note: undefined,
          created_at: "2026-07-23T19:27:25Z",
          updated_at: "2026-07-23T19:27:25Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof escalationsApi.useMyEscalations>);

    render(<MyEscalations />);
    expect(screen.getByText("Help Requests (1)")).toBeInTheDocument();
    expect(screen.getByText("Manifestation #2007")).toBeInTheDocument();
    expect(screen.getByText("author")).toBeInTheDocument();
    expect(screen.getByText("Alice Vincent")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  // ── 4.17 Deletion badge ─────────────────────────────────────────────────
  it("renders deletion badge for deletion request type", () => {
    vi.mocked(escalationsApi.useMyEscalations).mockReturnValue({
      data: [
        {
          id: 2,
          user_id: "user-1",
          manifestation_id: 2007,
          request_type: "deletion",
          field_name: "",
          suggested_value: "",
          note: "Duplicate entry",
          status: "pending",
          resolution_note: undefined,
          created_at: "2026-07-23T19:27:25Z",
          updated_at: "2026-07-23T19:27:25Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof escalationsApi.useMyEscalations>);

    render(<MyEscalations />);

    expect(screen.getByText("Help Requests (1)")).toBeInTheDocument();
    // Look for the translated "deletion" text (lower-case from mock)
    expect(screen.getByText("Deletion")).toBeInTheDocument();
  });

  // ── 4.18 Accepted status badge ─────────────────────────────────────────
  it("renders accepted status badge for accepted escalation", () => {
    vi.mocked(escalationsApi.useMyEscalations).mockReturnValue({
      data: [
        {
          id: 3,
          user_id: "user-1",
          manifestation_id: 2007,
          field_name: "title",
          suggested_value: "Fixed Title",
          status: "accepted",
          resolution_note: "Done",
          created_at: "2026-07-23T19:27:25Z",
          updated_at: "2026-07-23T19:27:25Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof escalationsApi.useMyEscalations>);

    render(<MyEscalations />);

    expect(screen.getByText("Accepted")).toBeInTheDocument();
    expect(screen.getByText("Fixed Title")).toBeInTheDocument();
  });

  // ── 4.19 Rejected status badge ─────────────────────────────────────────
  it("renders rejected status badge for rejected escalation", () => {
    vi.mocked(escalationsApi.useMyEscalations).mockReturnValue({
      data: [
        {
          id: 4,
          user_id: "user-1",
          manifestation_id: 2007,
          field_name: "isbn",
          suggested_value: "1234567890",
          status: "rejected",
          resolution_note: "Not valid",
          created_at: "2026-07-23T19:27:25Z",
          updated_at: "2026-07-23T19:27:25Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof escalationsApi.useMyEscalations>);

    render(<MyEscalations />);

    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });

  // ── 4.20 Resolution note visible ───────────────────────────────────────
  it("renders resolution note when present", () => {
    vi.mocked(escalationsApi.useMyEscalations).mockReturnValue({
      data: [
        {
          id: 5,
          user_id: "user-1",
          manifestation_id: 2007,
          field_name: "title",
          suggested_value: "Updated",
          status: "accepted",
          resolution_note: "Fixed via admin panel",
          created_at: "2026-07-23T19:27:25Z",
          updated_at: "2026-07-23T19:27:25Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof escalationsApi.useMyEscalations>);

    render(<MyEscalations />);

    expect(screen.getByText(/Fixed via admin panel/i)).toBeInTheDocument();
  });

  // ── 4.21 Target links clickable ────────────────────────────────────────
  it("renders target label as link with correct href", () => {
    vi.mocked(escalationsApi.useMyEscalations).mockReturnValue({
      data: [
        {
          id: 6,
          user_id: "user-1",
          manifestation_id: 99,
          field_name: "title",
          suggested_value: "Corrected",
          status: "pending",
          resolution_note: undefined,
          created_at: "2026-07-23T19:27:25Z",
          updated_at: "2026-07-23T19:27:25Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof escalationsApi.useMyEscalations>);

    render(<MyEscalations />);

    const targetLink = screen.getByText("Manifestation #99");
    expect(targetLink.closest("a")).toHaveAttribute("href", "/manifestation/99");
  });
});
