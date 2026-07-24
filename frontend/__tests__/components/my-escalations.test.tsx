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
});
