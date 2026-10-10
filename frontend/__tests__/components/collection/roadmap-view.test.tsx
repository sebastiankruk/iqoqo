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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// `vi.mock` factories are hoisted above module-level declarations, so every
// handle they close over has to come from `vi.hoisted`.
const {
  mockRoadmaps,
  mockCreateRoadmap,
  mockAddRoadmapItem,
  mockUpdateRoadmapItemTarget,
  mockDeleteRoadmapItem,
  mockReorderRoadmapItem,
  mockToast,
  mockManifestations,
  mockWorksShelf,
  mockExpressionsShelf,
  mockItems,
} = vi.hoisted(() => ({
  mockRoadmaps: vi.fn(),
  mockCreateRoadmap: vi.fn(),
  mockAddRoadmapItem: vi.fn(),
  mockUpdateRoadmapItemTarget: vi.fn(),
  mockDeleteRoadmapItem: vi.fn(),
  mockReorderRoadmapItem: vi.fn(),
  mockToast: { error: vi.fn(), success: vi.fn() },
  mockManifestations: vi.fn(),
  mockWorksShelf: vi.fn(),
  mockExpressionsShelf: vi.fn(),
  mockItems: vi.fn(),
}));

// The component imports these from the hooks barrel, not the roadmap module.
vi.mock("@/lib/api/hooks", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/hooks")>("@/lib/api/hooks");
  return {
    ...actual,
    useRoadmaps: () => mockRoadmaps(),
    useCreateRoadmap: () => ({ mutateAsync: mockCreateRoadmap }),
    useAddRoadmapItem: () => ({ mutateAsync: mockAddRoadmapItem }),
    useUpdateRoadmapItemTarget: () => ({ mutateAsync: mockUpdateRoadmapItemTarget }),
    useDeleteRoadmapItem: () => ({ mutateAsync: mockDeleteRoadmapItem }),
    useReorderRoadmapItem: () => ({ mutateAsync: mockReorderRoadmapItem }),
    useManifestations: (...args: unknown[]) => mockManifestations(...args),
    useWorksShelf: (...args: unknown[]) => mockWorksShelf(...args),
    useExpressionsShelf: (...args: unknown[]) => mockExpressionsShelf(...args),
    useItems: (...args: unknown[]) => mockItems(...args),
  };
});

vi.mock("sonner", () => ({ toast: mockToast }));

vi.mock("@/components/ui/dialog", async () => {
  const actual = await vi.importActual<typeof import("@/components/ui/dialog")>("@/components/ui/dialog");
  // Render dialog content inline so the forms are reachable without a portal.
  return { ...actual, DialogContent: ({ children }: { children?: React.ReactNode }) => <div>{children}</div> };
});

import { RoadmapView } from "@/components/collection/roadmap-view";

/**
 * Render the view inside a fresh QueryClient.
 *
 * @returns Nothing; rendering is the assertion subject.
 */
function renderView() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RoadmapView />
    </QueryClientProvider>
  );
}

/**
 * Build the shape `useRoadmaps` returns, narrowed to what the view destructures.
 *
 * @param overrides Fields to replace in the default state.
 * @returns The hook result the mocked `useRoadmaps` will hand back.
 */
function roadmapsState(overrides: Record<string, unknown> = {}) {
  return {
    data: [],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
    ...overrides,
  };
}

describe("RoadmapView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRoadmaps.mockReturnValue(roadmapsState());
    mockManifestations.mockReturnValue({ data: { data: [] } });
    mockWorksShelf.mockReturnValue({ data: { data: [] } });
    mockExpressionsShelf.mockReturnValue({ data: { data: [] } });
    mockItems.mockReturnValue({ data: { data: [] } });
  });

  it("does not present a failed request as an empty collection", async () => {
    mockRoadmaps.mockReturnValue(roadmapsState({ isError: true }));

    renderView();

    expect(await screen.findByText("Could not load your roadmaps")).toBeInTheDocument();
    expect(screen.queryByText("No Reading Roadmaps Yet")).not.toBeInTheDocument();
  });

  it("still shows the genuine empty state when the request succeeded", async () => {
    renderView();

    expect(await screen.findByText("No Reading Roadmaps Yet")).toBeInTheDocument();
    expect(screen.queryByText("Could not load your roadmaps")).not.toBeInTheDocument();
  });

  it("offers a retry that refetches", async () => {
    const refetch = vi.fn();
    mockRoadmaps.mockReturnValue(roadmapsState({ isError: true, refetch }));

    const user = userEvent.setup();
    renderView();

    await user.click(await screen.findByRole("button", { name: "Try again" }));

    expect(refetch).toHaveBeenCalled();
  });

  it("tells the user when creating a roadmap fails", async () => {
    mockCreateRoadmap.mockRejectedValue(new Error("boom"));

    const user = userEvent.setup();
    renderView();

    await user.click(await screen.findByRole("button", { name: /create roadmap/i }));
    const title = await screen.findByPlaceholderText("e.g. Distributed Systems Mastery 2026");
    await user.type(title, "Sci-fi backlog");
    await user.click(screen.getByRole("button", { name: /^create$/i }));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Could not create the roadmap. Please try again.");
    });
  });

  it("renders target level badges for all FRBR entities including Item", async () => {
    const roadmapWithItems = {
      id: 1,
      title: "FRBR Hierarchy Track",
      description: "Testing all 4 levels",
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
      items: [
        {
          id: 101,
          work_id: 1,
          expression_id: null,
          manifestation_id: null,
          item_id: null,
          target_type: "work" as const,
          title: "Abstract Work Alpha",
          creator: "Author A",
          position: 1,
          status: "queued",
          target_date: null,
          notes: null,
          completed_at: null,
        },
        {
          id: 102,
          work_id: null,
          expression_id: 2,
          manifestation_id: null,
          item_id: null,
          target_type: "expression" as const,
          title: "English Translation Beta",
          creator: "Translator B",
          position: 2,
          status: "queued",
          target_date: null,
          notes: null,
          completed_at: null,
        },
        {
          id: 103,
          work_id: null,
          expression_id: null,
          manifestation_id: 3,
          item_id: null,
          target_type: "manifestation" as const,
          title: "Hardcover Edition Gamma",
          creator: "Publisher C",
          position: 3,
          status: "queued",
          target_date: null,
          notes: null,
          completed_at: null,
          summary: { edition: "First Edition" },
        },
        {
          id: 104,
          work_id: null,
          expression_id: null,
          manifestation_id: null,
          item_id: 4,
          target_type: "item" as const,
          title: "Signed Physical Copy Delta",
          creator: "Author A",
          position: 4,
          status: "in_progress",
          target_date: null,
          notes: "My personal copy on shelf 2",
          completed_at: null,
          summary: { condition: "Like New" },
        },
      ],
    };

    mockRoadmaps.mockReturnValue(roadmapsState({ data: [roadmapWithItems] }));

    renderView();

    expect(await screen.findByRole("heading", { name: "FRBR Hierarchy Track" })).toBeInTheDocument();
    expect(screen.getByText("Abstract Work Alpha")).toBeInTheDocument();
    expect(screen.getByText("WORK")).toBeInTheDocument();
    expect(screen.getByText("English Translation Beta")).toBeInTheDocument();
    expect(screen.getByText("EXPRESSION")).toBeInTheDocument();
    expect(screen.getByText("Hardcover Edition Gamma")).toBeInTheDocument();
    expect(screen.getByText("MANIFESTATION")).toBeInTheDocument();
    expect(screen.getByText("First Edition")).toBeInTheDocument();
    expect(screen.getByText("Signed Physical Copy Delta")).toBeInTheDocument();
    expect(screen.getByText("Physical Copy")).toBeInTheDocument();
    expect(screen.getByText("Condition: Like New")).toBeInTheDocument();
  });

  it("allows switching target level to Copy (Item) and adding an owned item", async () => {
    const roadmap = {
      id: 1,
      title: "Reading Track",
      items: [],
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
    };
    mockRoadmaps.mockReturnValue(roadmapsState({ data: [roadmap] }));
    mockItems.mockReturnValue({
      data: {
        data: [
          {
            id: 99,
            title: "Physical Book Copy 99",
            publisher: "O'Reilly",
            collection_status: "owned",
          },
        ],
      },
    });

    const user = userEvent.setup();
    renderView();

    await user.click(await screen.findByTestId("add-to-roadmap-btn"));
    // Switch to Copy target level
    await user.click(screen.getByTestId("target-level-item"));

    // Candidate should be shown
    expect(await screen.findByText("Physical Book Copy 99")).toBeInTheDocument();

    // Select candidate
    await user.click(screen.getByTestId("select-item-0"));

    // Confirm Add
    await user.click(screen.getByTestId("confirm-add-item"));

    expect(mockAddRoadmapItem).toHaveBeenCalledWith(
      expect.objectContaining({
        roadmapId: 1,
        itemId: 99,
      })
    );
  });

  it("allows deleting an item from the roadmap", async () => {
    const roadmap = {
      id: 1,
      title: "Reading Track",
      items: [
        {
          id: 42,
          work_id: 1,
          title: "Book to Remove",
          creator: "Author",
          position: 1,
          status: "queued",
        },
      ],
      created_at: "2026-01-01",
      updated_at: "2026-01-01",
    };
    mockRoadmaps.mockReturnValue(roadmapsState({ data: [roadmap] }));

    const user = userEvent.setup();
    renderView();

    await user.click(await screen.findByTestId("delete-item-btn"));

    expect(mockDeleteRoadmapItem).toHaveBeenCalledWith(42);
  });
});
