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
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import enMessages from "@/messages/en.json";
import { ManualEntryForm } from "@/components/scanner/manual-entry-form";
import { SerialDisambiguationModal } from "@/components/scanner/serial-disambiguation-modal";
import { WorkDetailClient } from "@/components/work/work-detail-client";
import type { IsbnMeta, WorkDetail } from "@/types/frbr";

const mockUseWork = vi.fn();
const mockUseProfile = vi.fn();

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="footer" />,
}));

vi.mock("next-intl", () => ({
  useTranslations: (ns?: string) => {
    const getDict = () => {
      if (ns === "SerialIssues") return enMessages.SerialIssues as Record<string, unknown>;
      if (ns === "WorkRollup") return enMessages.WorkRollup as Record<string, unknown>;
      if (ns === "Wishlist") return enMessages.Wishlist as Record<string, unknown>;
      return enMessages.scanner as Record<string, unknown>;
    };
    return (key: string, params?: Record<string, string>) => {
      const parts = key.split(".");
      let cur: unknown = getDict();
      for (const p of parts) {
        if (cur && typeof cur === "object" && p in cur) {
          cur = (cur as Record<string, unknown>)[p];
        } else {
          cur = key;
          break;
        }
      }
      let out = typeof cur === "string" ? cur : key;
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          out = out.replace(`{${k}}`, v);
        }
      }
      return out;
    };
  },
}));

vi.mock("@/lib/api/hooks", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/hooks")>();
  return {
    ...actual,
    useWork: (id: number, initial?: WorkDetail | null) => mockUseWork(id, initial),
    useProfile: () => mockUseProfile(),
  };
});

vi.mock("@/lib/api/wishlist", async importOriginal => {
  const actual = await importOriginal<typeof import("@/lib/api/wishlist")>();
  return {
    ...actual,
    useWishlist: () => ({ data: { data: [] } }),
    useCreateWishlistItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useDeleteWishlistItem: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

/** Render element inside a fresh non-retrying QueryClientProvider. */
function renderWithQuery(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("C132 Serial Scanner & Issues Browser UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseProfile.mockReturnValue({ data: { id: "u1", username: "collector" } });
  });

  it("renders SerialDisambiguationModal with existing issues and Add New Issue CTA", () => {
    const onSelectIssue = vi.fn();
    const onAddNewIssue = vi.fn();
    const disambig: IsbnMeta = {
      Title: "National Geographic Polska",
      title: "National Geographic Polska",
      Authors: [],
      issn: "1507-5966",
      ean: "9771507596044",
      serial_disambiguation: true,
      existing_issues: [
        {
          manifestation_id: 71,
          issue_number: "7",
          cumulative_issue_number: 58,
          publication_year: 2004,
          publication_month: 7,
          full_barcode: "977150759604407",
          cover_headline: "Skarby pod lodem",
        },
      ],
    };

    render(
      <SerialDisambiguationModal
        disambiguation={disambig}
        onSelectIssue={onSelectIssue}
        onAddNewIssue={onAddNewIssue}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByText("ISSN 1507-5966")).toBeInTheDocument();
    expect(screen.getByText("7(58)")).toBeInTheDocument();
    expect(screen.getByText("Skarby pod lodem")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("serial-issue-option-71"));
    expect(onSelectIssue).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId("add-new-serial-issue-button"));
    expect(onAddNewIssue).toHaveBeenCalledTimes(1);
  });

  it("renders Snap Cover to Auto-Fill Issue button inside SerialDisambiguationModal when handler is supplied", () => {
    const onSnapCoverAutoFill = vi.fn();
    const disambig: IsbnMeta = {
      Title: "National Geographic Polska",
      title: "National Geographic Polska",
      Authors: [],
      issn: "1507-5966",
      ean: "9771507596044",
      serial_disambiguation: true,
      existing_issues: [],
    };

    render(
      <SerialDisambiguationModal
        disambiguation={disambig}
        onSelectIssue={vi.fn()}
        onAddNewIssue={vi.fn()}
        onSnapCoverAutoFill={onSnapCoverAutoFill}
        onDismiss={vi.fn()}
      />
    );

    expect(screen.getByTestId("snap-cover-serial-autofill")).toBeInTheDocument();
    expect(screen.getByText("Snap Cover to Auto-Fill Issue")).toBeInTheDocument();
  });

  it("renders serial issue inputs in ManualEntryForm when format is magazine", () => {
    renderWithQuery(
      <ManualEntryForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        initialFormat="magazine"
        initialTitle="National Geographic Polska"
        initialIssn="1507-5966"
        initialIssueNumber="12"
      />
    );

    expect(screen.getByTestId("serial-manual-fields")).toBeInTheDocument();
    expect((screen.getByLabelText("ISSN") as HTMLInputElement).value).toBe("1507-5966");
    expect((screen.getByLabelText("Issue #") as HTMLInputElement).value).toBe("12");
  });

  it("renders chronological 'Issues in this Serial' grouped by year on WorkDetailClient", () => {
    const serialWork: WorkDetail = {
      id: 90,
      title: "National Geographic Polska",
      authors: [],
      issn: "1507-5966",
      work_kind: "serial",
      expressions: [
        {
          id: 901,
          work_id: 90,
          content_type: "text",
          language: "pl",
          manifestations: [
            {
              id: 503,
              issue_number: "12",
              cumulative_issue_number: 63,
              publication_year: 2004,
              publication_month: 12,
              full_barcode: "977150759604412",
            },
            {
              id: 501,
              issue_number: "11",
              cumulative_issue_number: 50,
              publication_year: 2003,
              publication_month: 11,
              full_barcode: "977150759603711",
            },
            {
              id: 502,
              issue_number: "7",
              cumulative_issue_number: 58,
              publication_year: 2004,
              publication_month: 7,
              full_barcode: "977150759604407",
            },
            {
              id: 504,
              issue_number: "1",
              cumulative_issue_number: 64,
              publication_year: 2005,
              publication_month: 1,
              full_barcode: "977150759650101",
            },
            {
              id: 505,
              issue_number: "6",
              cumulative_issue_number: 69,
              publication_year: 2005,
              publication_month: 6,
              full_barcode: "977150759650106",
            },
          ],
        },
      ],
    };
    mockUseWork.mockReturnValue({ data: serialWork, isLoading: false });

    renderWithQuery(<WorkDetailClient workId={90} initialWork={serialWork} />);

    expect(screen.getByTestId("work-issn-badge").textContent).toBe("ISSN 1507-5966");
    expect(screen.getByTestId("work-add-issue-cta")).toBeInTheDocument();
    const section = screen.getByTestId("serial-issues-section");
    expect(section).toBeInTheDocument();
    ["11 (50)", "7 (58)", "12 (63)", "1 (64)", "6 (69)"].forEach(label => {
      expect(section.textContent).toContain(label);
    });
  });
});
