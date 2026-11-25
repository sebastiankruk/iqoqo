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

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkLinkReviewer } from "@/components/admin/work-link-reviewer";
import * as adminApi from "@/lib/api/admin";
import * as catalogHooks from "@/lib/api/hooks/catalog";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/lib/api/hooks/catalog", () => ({
  useCatalogGraphSearch: vi.fn(),
}));

describe("WorkLinkReviewer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(catalogHooks.useCatalogGraphSearch).mockReturnValue({
      data: [{ entity_type: "work", entity_id: 42, label: "The Hobbit", subtitle: "text", url: "/work/42" }],
      isLoading: false,
    } as unknown as ReturnType<typeof catalogHooks.useCatalogGraphSearch>);
  });

  it("renders null confidence safely, supports candidate direction swap, and uses Cancel on unlink", async () => {
    vi.spyOn(adminApi, "listWorkLinkCandidates").mockResolvedValue({
      items: [
        {
          id: 99,
          source_work_id: 1,
          target_work_id: 2,
          source_work_title: "Book Work",
          target_work_title: "Film Work",
          source_categories: ["text"],
          target_categories: ["movie"],
          proposed_relation_type: "is_adaptation_of",
          confidence: null as unknown as number,
          resolution_source: "heuristic",
          status: "pending",
          llm_reasoning: null,
          created_at: null,
          resolved_at: null,
        },
      ],
      total: 1,
    });
    const acceptSpy = vi.spyOn(adminApi, "acceptWorkLinkCandidate").mockResolvedValue({} as never);
    vi.spyOn(adminApi, "listWorkRelations").mockResolvedValue({
      items: [
        {
          id: 7,
          source_work_id: 10,
          target_work_id: 20,
          source_work_title: "Dune Film",
          target_work_title: "Dune Book",
          source_categories: ["movie"],
          target_categories: ["text"],
          relation_type: "is_adaptation_of",
          notes: null,
          created_at: null,
          updated_at: null,
        },
      ],
      total: 1,
    });

    render(<WorkLinkReviewer canEdit={true} />);
    expect(await screen.findByText("—")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "swapDirection" }));
    fireEvent.click(screen.getByRole("button", { name: "accept" }));
    expect(acceptSpy).toHaveBeenCalledWith(99, {
      relation_type: "is_adaptation_of",
      source_work_id: 2,
      target_work_id: 1,
    });

    fireEvent.click(screen.getByRole("button", { name: /confirmedTab/ }));
    fireEvent.click(await screen.findByRole("button", { name: "unlink" }));
    expect(await screen.findByRole("button", { name: "cancel" })).toBeInTheDocument();
  });

  it("consumes useCatalogGraphSearch data envelope in manual link dialog", async () => {
    vi.spyOn(adminApi, "listWorkLinkCandidates").mockResolvedValue({ items: [], total: 0 });
    vi.spyOn(adminApi, "listWorkRelations").mockResolvedValue({ items: [], total: 0 });

    render(<WorkLinkReviewer canEdit={true} />);
    fireEvent.click(await screen.findByRole("button", { name: "manualLinkButton" }));
    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0], { target: { value: "Hobbit" } });
    const options = await screen.findAllByText("The Hobbit (#42)");
    expect(options.length).toBeGreaterThanOrEqual(1);
    fireEvent.click(options[0]);
  });
});
