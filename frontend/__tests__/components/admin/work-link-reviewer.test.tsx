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

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkLinkReviewer } from "@/components/admin/work-link-reviewer";
import * as adminApi from "@/lib/api/admin";

vi.mock("@/lib/api/admin", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/admin")>("@/lib/api/admin");
  return {
    ...actual,
    listWorkLinkCandidates: vi.fn(),
    listWorkRelations: vi.fn(),
    acceptWorkLinkCandidate: vi.fn(),
    dismissWorkLinkCandidate: vi.fn(),
    scanWorkLinks: vi.fn(),
  };
});

describe("WorkLinkReviewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(adminApi.listWorkLinkCandidates).mockResolvedValue({
      items: [
        {
          id: 11,
          source_work_id: 2,
          target_work_id: 1,
          source_work_title: "The Lord of the Rings: The Fellowship of the Ring",
          target_work_title: "The Lord of the Rings",
          source_categories: ["movie"],
          target_categories: ["book"],
          proposed_relation_type: "is_adaptation_of",
          confidence: 0.92,
          resolution_source: "heuristic",
          llm_reasoning: null,
          status: "pending",
          created_at: "2026-11-24T00:00:00Z",
          resolved_at: null,
        },
        {
          id: 12,
          source_work_id: 4,
          target_work_id: 3,
          source_work_title: "Harry Potter and the Sorcerer's Stone",
          target_work_title: "Harry Potter and the Philosopher's Stone",
          source_categories: ["movie"],
          target_categories: ["book"],
          proposed_relation_type: "is_adaptation_of",
          confidence: 0.96,
          resolution_source: "llm",
          llm_reasoning: "US film adaptation of UK novel",
          status: "pending",
          created_at: "2026-11-24T00:00:00Z",
          resolved_at: null,
        },
      ],
      total: 2,
    });
    vi.mocked(adminApi.listWorkRelations).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(adminApi.acceptWorkLinkCandidate).mockResolvedValue({
      candidate: {} as adminApi.WorkLinkCandidate,
      relation: {} as adminApi.WorkRelationItem,
    });
    vi.mocked(adminApi.dismissWorkLinkCandidate).mockResolvedValue({} as adminApi.WorkLinkCandidate);
  });

  it("renders heuristic and LLM provenance badges and supports accept/dismiss", async () => {
    render(<WorkLinkReviewer canEdit={true} />);

    await waitFor(() => {
      expect(screen.getByText("The Lord of the Rings: The Fellowship of the Ring")).toBeInTheDocument();
      expect(screen.getByText("US film adaptation of UK novel")).toBeInTheDocument();
    });

    expect(screen.getByText("Heuristic")).toBeInTheDocument();
    expect(screen.getByText("LLM")).toBeInTheDocument();

    const acceptButtons = screen.getAllByRole("button", { name: /confirm link/i });
    fireEvent.click(acceptButtons[0]);

    await waitFor(() => {
      expect(adminApi.acceptWorkLinkCandidate).toHaveBeenCalledWith(11, { relation_type: "is_adaptation_of" });
    });

    const dismissButtons = screen.getAllByRole("button", { name: /dismiss/i });
    fireEvent.click(dismissButtons[1]);

    await waitFor(() => {
      expect(adminApi.dismissWorkLinkCandidate).toHaveBeenCalledWith(12);
    });
  });
});
