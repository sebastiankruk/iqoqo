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
const { mockRoadmaps, mockCreateRoadmap, mockAddRoadmapItem, mockReorderRoadmapItem, mockToast } = vi.hoisted(() => ({
  mockRoadmaps: vi.fn(),
  mockCreateRoadmap: vi.fn(),
  mockAddRoadmapItem: vi.fn(),
  mockReorderRoadmapItem: vi.fn(),
  mockToast: { error: vi.fn(), success: vi.fn() },
}));

// The component imports these from the hooks barrel, not the roadmap module.
vi.mock("@/lib/api/hooks", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/hooks")>("@/lib/api/hooks");
  return {
    ...actual,
    useRoadmaps: () => mockRoadmaps(),
    useCreateRoadmap: () => ({ mutateAsync: mockCreateRoadmap }),
    useAddRoadmapItem: () => ({ mutateAsync: mockAddRoadmapItem }),
    useReorderRoadmapItem: () => ({ mutateAsync: mockReorderRoadmapItem }),
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
  });

  it("does not present a failed request as an empty collection", async () => {
    // The defect: `useRoadmaps()` was destructured for `data` and `isLoading`
    // only, so a rejected query left `data` undefined, `roadmaps` defaulted to
    // `[]`, and the component rendered "No Reading Roadmaps Yet" -- telling the
    // user they have none when in fact the list could not be fetched. The empty
    // state also invites them to create their first roadmap, which cannot
    // succeed while the request is failing.
    mockRoadmaps.mockReturnValue(roadmapsState({ isError: true }));

    renderView();

    expect(await screen.findByText("Could not load your roadmaps")).toBeInTheDocument();
    expect(screen.queryByText("No Reading Roadmaps Yet")).not.toBeInTheDocument();
  });

  it("still shows the genuine empty state when the request succeeded", async () => {
    // The control for the test above: the fix must not turn an ordinary empty
    // collection into an error.
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
    // All three mutation handlers caught, logged to the console, and returned.
    // The user clicked, nothing happened, and there was no way to tell a failed
    // save from a click that did not register.
    mockCreateRoadmap.mockRejectedValue(new Error("boom"));

    const user = userEvent.setup();
    renderView();

    // The add-item dialog also renders a textbox, so the title field is targeted
    // by its own placeholder rather than by role alone.
    await user.click(await screen.findByRole("button", { name: /create roadmap/i }));
    const title = await screen.findByPlaceholderText("e.g. Distributed Systems Mastery 2026");
    await user.type(title, "Sci-fi backlog");
    await user.click(screen.getByRole("button", { name: /^create$/i }));

    await waitFor(() => {
      expect(mockToast.error).toHaveBeenCalledWith("Could not create the roadmap. Please try again.");
    });
  });
});
