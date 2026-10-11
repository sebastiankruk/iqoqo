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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProviderMergeDialog, type FieldComparison } from "@/components/admin/provider-merge-dialog";
import * as adminApi from "@/lib/api/admin";
import { toast } from "sonner";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ open, children }: any) => (open ? <div data-testid="dialog">{children}</div> : null),
  DialogContent: ({ children, className }: any) => <div className={className}>{children}</div>,
  DialogHeader: ({ children }: any) => <div>{children}</div>,
  DialogTitle: ({ children }: any) => <h2>{children}</h2>,
  DialogDescription: ({ children }: any) => <p>{children}</p>,
  DialogFooter: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/components/ui/card", () => ({
  Card: ({ children }: any) => <div data-testid="card">{children}</div>,
  CardHeader: ({ children }: any) => <div>{children}</div>,
  CardTitle: ({ children }: any) => <h3>{children}</h3>,
  CardContent: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));

const mockTree: adminApi.FrbrTree = {
  work: {
    id: 1,
    title: "Dune",
    meta: {
      authors: ["Frank Herbert"],
      description: "Sci-fi classic",
      _provenance: { title: "google_books", authors: "open_library" },
    },
  },
  expression: {
    id: 2,
    work_id: 1,
    content_type: "text",
    language: "en",
    meta: {
      _provenance: { language: "google_books" },
    },
  },
  manifestation: {
    id: 3,
    expression_id: 2,
    isbn13: "9780441172719",
    upc: null,
    ean: null,
    publisher: "Chilton Books",
    publication_date: "1965",
    meta: {
      cover_url: "https://example.com/cover.jpg",
      _provenance: { publisher: "open_library", cover_url: "google_books" },
    },
  },
  items: [],
};

const customComparisons: FieldComparison[] = [
  {
    fieldKey: "title",
    fieldLabel: "Title",
    tier: "work",
    currentValue: "Dune",
    candidates: [
      { provider: "google_books", providerLabel: "Google Books", value: "Dune" },
      { provider: "open_library", providerLabel: "Open Library", value: "Dune: Special Edition" },
    ],
  },
  {
    fieldKey: "publisher",
    fieldLabel: "Publisher",
    tier: "manifestation",
    currentValue: "Chilton",
    candidates: [
      { provider: "google_books", providerLabel: "Google Books", value: "Chilton" },
      { provider: "open_library", providerLabel: "Open Library", value: "Chilton Books Press" },
    ],
  },
];

/**
 * Helper to render components wrapped with QueryClientProvider.
 *
 * @param ui - The React element to render.
 * @returns Render result.
 */
function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ProviderMergeDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders side-by-side candidate fragments grouped by FRBR tier", () => {
    renderWithClient(<ProviderMergeDialog open={true} onOpenChange={vi.fn()} manifestationId={3} tree={mockTree} />);

    expect(screen.getByText("Merge Provider Metadata")).toBeInTheDocument();
    expect(screen.getByText("Work Tier (Creation)")).toBeInTheDocument();
    expect(screen.getByText("Expression Tier (Realization)")).toBeInTheDocument();
    expect(screen.getByText("Manifestation Tier (Embodiment)")).toBeInTheDocument();

    // Check candidate cards exist
    expect(screen.getByTestId("candidate-title-google_books")).toBeInTheDocument();
    expect(screen.getByTestId("candidate-publisher-google_books")).toBeInTheDocument();
  });

  it("allows selecting candidates and submits reconciled payload", async () => {
    const mergeSpy = vi.spyOn(adminApi, "mergeCustodianProviderMetadata").mockResolvedValue({
      manifestation_id: 3,
      expression_id: 2,
      work_id: 1,
      diff: {},
    });
    const onOpenChange = vi.fn();
    const onSuccess = vi.fn();

    renderWithClient(
      <ProviderMergeDialog
        open={true}
        onOpenChange={onOpenChange}
        manifestationId={3}
        customFields={customComparisons}
        onSuccess={onSuccess}
      />
    );

    // Select Open Library for title
    const openLibraryTitleCandidate = screen.getByTestId("candidate-title-open_library");
    fireEvent.click(openLibraryTitleCandidate);

    // Submit merge
    const submitBtn = screen.getByTestId("provider-merge-submit-btn");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mergeSpy).toHaveBeenCalledTimes(1);
    });

    expect(mergeSpy).toHaveBeenCalledWith(3, {
      work: {
        title: {
          value: "Dune: Special Edition",
          provider: "open_library",
        },
      },
      expression: {},
      manifestation: {
        publisher: {
          value: "Chilton",
          provider: "google_books",
        },
      },
    });

    expect(toast.success).toHaveBeenCalledWith("Provider metadata merged successfully");
    expect(onSuccess).toHaveBeenCalled();
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("handles merge submission failure gracefully with error toast", async () => {
    vi.spyOn(adminApi, "mergeCustodianProviderMetadata").mockRejectedValue(new Error("Database locked"));

    renderWithClient(
      <ProviderMergeDialog open={true} onOpenChange={vi.fn()} manifestationId={3} customFields={customComparisons} />
    );

    const submitBtn = screen.getByTestId("provider-merge-submit-btn");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Database locked");
    });
  });
});
