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

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { DuplicateReviewer } from "@/components/admin/duplicate-reviewer";
import type { DuplicateCandidate } from "@/lib/api/admin";

vi.mock("@/lib/api/admin", () => ({
  getDuplicateCandidates: vi.fn(),
  dismissDuplicateCandidate: vi.fn(),
  mergeDuplicateCandidate: vi.fn(),
  runDuplicateScan: vi.fn(),
}));

import {
  getDuplicateCandidates,
  dismissDuplicateCandidate,
  mergeDuplicateCandidate,
  runDuplicateScan,
} from "@/lib/api/admin";
import { toast } from "sonner";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const WORK_CANDIDATE: DuplicateCandidate = {
  id: 1,
  entity_tier: "work",
  source_id: 10,
  target_id: 11,
  confidence: 0.93,
  resolution_source: "llama",
  llm_reasoning: "Identical title, author, and first-publication year.",
  status: "pending",
  created_at: "2026-01-01T00:00:00Z",
  resolved_at: null,
  resolved_by_id: null,
  resolved_by_email: null,
  source: {
    tier: "work",
    id: 10,
    title: "The Dispossessed",
    sort_title: "dispossessed, the",
    creators: ["guin k le ursula"],
    expression_count: 2,
    genres: "Science Fiction",
    description_present: true,
  },
  target: {
    tier: "work",
    id: 11,
    title: "The Dispossessed",
    sort_title: "the dispossessed",
    creators: ["le guin ursula k"],
    expression_count: 1,
    genres: null,
    description_present: false,
  },
};

const MANIFESTATION_CANDIDATE: DuplicateCandidate = {
  ...WORK_CANDIDATE,
  id: 2,
  entity_tier: "manifestation",
  source_id: 20,
  target_id: 21,
  confidence: 0.78,
  resolution_source: "llama",
  llm_reasoning: "Same edition, different metadata source.",
  source: {
    tier: "manifestation",
    id: 20,
    title: "The Dispossessed",
    creators: ["le guin ursula k"],
    isbn13: "9780060512750",
    ean: null,
    upc: null,
    barcode: null,
    format: "Paperback",
    publisher: "Harper & Row",
    publication_date: "1975-05-01",
    label: null,
    catalog_number: null,
    language: "en",
    content_type: "text",
    work_title: "The Dispossessed",
    work_id: 10,
    item_count: 1,
    cover_url: null,
  },
  target: {
    tier: "manifestation",
    id: 21,
    title: "The Dispossessed",
    creators: ["le guin ursula k"],
    isbn13: "9780060512750",
    ean: null,
    upc: null,
    barcode: null,
    format: "Paperback",
    publisher: null,
    publication_date: null,
    label: null,
    catalog_number: "HAR-1975",
    language: null,
    content_type: null,
    work_title: "The Dispossessed",
    work_id: 11,
    item_count: 0,
    cover_url: null,
  },
};

const EXPRESSION_CANDIDATE: DuplicateCandidate = {
  ...WORK_CANDIDATE,
  id: 5,
  entity_tier: "expression",
  source_id: 30,
  target_id: 31,
  confidence: null,
  resolution_source: "heuristic",
  llm_reasoning: "heuristic: identical normalized label; identical language; identical content_type",
  source: {
    tier: "expression",
    id: 30,
    label: "The Dispossessed (English text)",
    language: "en",
    content_type: "text",
    manifestation_count: 2,
    creators: ["le guin ursula k"],
    cover_url: null,
  },
  target: {
    tier: "expression",
    id: 31,
    label: "The Dispossessed (English text)",
    language: "en",
    content_type: "text",
    manifestation_count: 1,
    creators: ["le guin ursula k"],
    cover_url: null,
  },
};

/**
 * Stub the candidate queue with the given rows.
 *
 * @param candidates - Rows the mocked client should resolve to.
 * @param total - Total row count reported in the pagination meta.
 * @returns Nothing; it only installs the mock.
 */
function mockQueue(candidates: DuplicateCandidate[], total = candidates.length) {
  vi.mocked(getDuplicateCandidates).mockResolvedValue({ data: candidates, meta: { total, page: 1, limit: 10 } });
}

describe("DuplicateReviewer Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockQueue([]);
  });

  describe("Queue rendering", () => {
    it("shows an empty state when there are no candidates", async () => {
      render(<DuplicateReviewer canEdit />);

      expect(await screen.findByText("No duplicate candidates")).toBeInTheDocument();
      expect(screen.getByTestId("duplicate-total")).toHaveTextContent("0 candidates awaiting review");
    });

    it("renders both sides of a Work pair with creators, genres, and child counts", async () => {
      mockQueue([WORK_CANDIDATE]);
      render(<DuplicateReviewer canEdit />);

      expect(await screen.findByTestId("duplicate-candidate-1")).toBeInTheDocument();
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("The Dispossessed");
      expect(screen.getByTestId("duplicate-side-B")).toHaveTextContent("The Dispossessed");
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("Science Fiction");
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("2");
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("guin k le ursula");
      // The LLM rationale is surfaced to the reviewer.
      expect(screen.getByText("Identical title, author, and first-publication year.")).toBeInTheDocument();
    });

    it("shows ISBNs for Manifestation pairs, where they are edition-defining", async () => {
      mockQueue([MANIFESTATION_CANDIDATE]);
      render(<DuplicateReviewer canEdit />);

      expect(await screen.findByTestId("duplicate-candidate-2")).toBeInTheDocument();
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("9780060512750");
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("Harper & Row");
      expect(screen.getByTestId("duplicate-side-B")).toHaveTextContent("HAR-1975");
    });

    it("renders both sides of an Expression pair with language, content type, and manifestation count", async () => {
      mockQueue([EXPRESSION_CANDIDATE]);
      render(<DuplicateReviewer canEdit />);

      expect(await screen.findByTestId("duplicate-candidate-5")).toBeInTheDocument();
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("The Dispossessed (English text)");
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("en");
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("text");
      expect(screen.getByTestId("duplicate-side-A")).toHaveTextContent("2");
      expect(screen.getByTestId("duplicate-side-B")).toHaveTextContent("1");
    });

    it("labels a model verdict as an LLM confidence percentage", async () => {
      mockQueue([WORK_CANDIDATE, MANIFESTATION_CANDIDATE]);
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-1");
      const badges = screen.getAllByTestId("confidence-badge");
      expect(badges[0]).toHaveTextContent("LLM 93% match");
      expect(badges[0]).toHaveAttribute("data-provenance", "llama");
      expect(badges[1]).toHaveTextContent("LLM 78% match");
    });

    // A classifier verdict is categorical, not probabilistic. Rendering it as a
    // percentage would present a rule as a calibrated belief, and a null
    // confidence would otherwise render as a bare "0% match".
    it("renders a classifier verdict as a match with no number", async () => {
      const heuristic: DuplicateCandidate = {
        ...WORK_CANDIDATE,
        id: 3,
        confidence: null,
        resolution_source: "heuristic",
        llm_reasoning: "heuristic: identical normalized title; shared creator(s): le guin ursula k",
      };
      mockQueue([heuristic]);
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-3");
      const badge = screen.getByTestId("confidence-badge");
      expect(badge).toHaveAttribute("data-provenance", "heuristic");
      expect(badge).toHaveTextContent("match (rules)");
      expect(badge).not.toHaveTextContent("%");
      expect(badge).not.toHaveTextContent("0%");
    });

    it("treats a null confidence as a classifier verdict even if provenance is missing", async () => {
      const legacy: DuplicateCandidate = {
        ...WORK_CANDIDATE,
        id: 4,
        confidence: null,
        resolution_source: undefined as unknown as DuplicateCandidate["resolution_source"],
      };
      mockQueue([legacy]);
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-4");
      expect(screen.getByTestId("confidence-badge")).toHaveAttribute("data-provenance", "heuristic");
    });
  });

  describe("Primary entity selection", () => {
    it("defaults to the source entity as primary and allows switching to the target", async () => {
      mockQueue([WORK_CANDIDATE]);
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-1");
      expect(screen.getByText("Merge keeping entity 10")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Keep this one" }));
      expect(screen.getByText("Merge keeping entity 11")).toBeInTheDocument();
    });
  });

  describe("Merge confirmation", () => {
    it("requires confirmation before merging and passes the chosen primary", async () => {
      mockQueue([WORK_CANDIDATE]);
      vi.mocked(mergeDuplicateCandidate).mockResolvedValue({
        candidate_id: 1,
        entity_tier: "work",
        primary_id: 10,
        merged_id: 11,
      });
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-1");
      // The destructive confirmation dialog is not open until the merge is requested.
      expect(screen.queryByText("Merge these entities?")).not.toBeInTheDocument();

      fireEvent.click(screen.getByText("Merge keeping entity 10"));
      expect(await screen.findByText("Merge these entities?")).toBeInTheDocument();
      expect(mergeDuplicateCandidate).not.toHaveBeenCalled();

      fireEvent.click(screen.getByRole("button", { name: "Merge permanently" }));

      await waitFor(() => expect(mergeDuplicateCandidate).toHaveBeenCalledWith(1, 10));
      expect(toast.success).toHaveBeenCalledWith("Merged into entity 10");
    });

    it("cancelling the confirmation does not merge", async () => {
      mockQueue([WORK_CANDIDATE]);
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-1");
      fireEvent.click(screen.getByText("Merge keeping entity 10"));
      expect(await screen.findByText("Merge these entities?")).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
      await waitFor(() => expect(screen.queryByText("Merge these entities?")).not.toBeInTheDocument());
      expect(mergeDuplicateCandidate).not.toHaveBeenCalled();
    });

    it("surfaces a rollback failure to the reviewer", async () => {
      mockQueue([WORK_CANDIDATE]);
      vi.mocked(mergeDuplicateCandidate).mockRejectedValue(new Error("Merge failed and was rolled back"));
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-1");
      fireEvent.click(screen.getByText("Merge keeping entity 10"));
      fireEvent.click(await screen.findByRole("button", { name: "Merge permanently" }));

      await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Merge failed and was rolled back"));
    });
  });

  describe("Dismissal", () => {
    it("dismisses a false positive and reloads the queue", async () => {
      mockQueue([WORK_CANDIDATE]);
      vi.mocked(dismissDuplicateCandidate).mockResolvedValue({ ...WORK_CANDIDATE, status: "dismissed" });
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-1");
      fireEvent.click(screen.getByRole("button", { name: /Not duplicates/ }));

      await waitFor(() => expect(dismissDuplicateCandidate).toHaveBeenCalledWith(1));
      expect(toast.success).toHaveBeenCalledWith("Candidate dismissed");
      await waitFor(() => expect(getDuplicateCandidates).toHaveBeenCalledTimes(2));
    });
  });

  describe("Scan", () => {
    it("triggers a scan and reloads the queue", async () => {
      vi.mocked(runDuplicateScan).mockResolvedValue({
        tier: "all",
        threshold: 0.8,
        dry_run: false,
        entities_screened: 120,
        candidate_pairs: 4,
        llm_evaluations: 3,
        llm_failures: 0,
        below_threshold: 1,
        already_known: 0,
        created: 2,
        work_candidates: 3,
        expression_candidates: 0,
        manifestation_candidates: 1,
      });
      render(<DuplicateReviewer canEdit />);

      await screen.findByText("No duplicate candidates");
      fireEvent.click(screen.getByRole("button", { name: /Run scan/ }));

      await waitFor(() => expect(runDuplicateScan).toHaveBeenCalledWith({ tier: "all" }));
      expect(toast.success).toHaveBeenCalledWith("Scan queued 2 new candidate(s)");
    });

    it("reports a scan failure", async () => {
      vi.mocked(runDuplicateScan).mockRejectedValue(new Error("Ollama unreachable at http://localhost:11434"));
      render(<DuplicateReviewer canEdit />);

      await screen.findByText("No duplicate candidates");
      fireEvent.click(screen.getByRole("button", { name: /Run scan/ }));

      await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Ollama unreachable at http://localhost:11434"));
    });
  });

  describe("Read-only access", () => {
    it("hides destructive controls from viewers without metadata write permission", async () => {
      mockQueue([WORK_CANDIDATE]);
      render(<DuplicateReviewer canEdit={false} />);

      await screen.findByTestId("duplicate-candidate-1");
      expect(screen.queryByRole("button", { name: /Not duplicates/ })).not.toBeInTheDocument();
      expect(screen.queryByText(/Merge keeping entity/)).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Run scan/ })).not.toBeInTheDocument();
      // The comparison itself remains available so a reviewer can still assess the pair.
      expect(screen.getByTestId("duplicate-side-A")).toBeInTheDocument();
    });

    // Button density is a UX constraint: a candidate card must not grow more
    // controls as tiers are added, so these counts are pinned.  A read-only
    // viewer keeps the two primary toggles, which only change which side is
    // highlighted; the destructive controls are gone.
    it("keeps the read-only card's control count unchanged", async () => {
      mockQueue([WORK_CANDIDATE, MANIFESTATION_CANDIDATE, EXPRESSION_CANDIDATE]);
      render(<DuplicateReviewer canEdit={false} />);

      await screen.findByTestId("duplicate-candidate-1");
      const labels = within(screen.getByTestId("duplicate-candidate-1"))
        .getAllByRole("button")
        .map(b => b.textContent?.trim());
      expect(labels).toEqual(["Primary selected", "Keep this one"]);

      const exprLabels = within(screen.getByTestId("duplicate-candidate-5"))
        .getAllByRole("button")
        .map(b => b.textContent?.trim());
      expect(exprLabels).toEqual(["Primary selected", "Keep this one"]);

      // The only view-level action left is Refresh.
      const viewButtons = screen.getAllByRole("button").map(b => b.textContent?.trim());
      expect(viewButtons).toEqual([
        "Refresh",
        "Primary selected",
        "Keep this one",
        "Primary selected",
        "Keep this one",
        "Primary selected",
        "Keep this one",
      ]);
    });

    it("keeps the editable card's control count fixed as tiers are added", async () => {
      mockQueue([WORK_CANDIDATE, MANIFESTATION_CANDIDATE, EXPRESSION_CANDIDATE]);
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-1");
      const labels = (testId: string) =>
        within(screen.getByTestId(testId))
          .getAllByRole("button")
          .map(b => b.textContent?.trim());

      // Dismiss, two primary toggles, and the merge action.  The Expression
      // tier must reuse this exact card rather than adding to it.
      expect(labels("duplicate-candidate-1")).toEqual([
        "Not duplicates",
        "Primary selected",
        "Keep this one",
        "Merge keeping entity 10",
      ]);
      expect(labels("duplicate-candidate-2")).toEqual([
        "Not duplicates",
        "Primary selected",
        "Keep this one",
        "Merge keeping entity 20",
      ]);
      expect(labels("duplicate-candidate-5")).toEqual([
        "Not duplicates",
        "Primary selected",
        "Keep this one",
        "Merge keeping entity 30",
      ]);
    });
  });

  describe("Missing entities", () => {
    it("reports a side whose entity no longer exists instead of crashing", async () => {
      mockQueue([{ ...WORK_CANDIDATE, target: null }]);
      render(<DuplicateReviewer canEdit />);

      await screen.findByTestId("duplicate-candidate-1");
      expect(screen.getByText("Entity no longer exists")).toBeInTheDocument();
      // Merging is disabled while either side is missing.
      expect(screen.getByText("Merge keeping entity 10").closest("button")).toBeDisabled();
    });
  });
});
