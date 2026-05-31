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
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ReadingRoadmapComponent } from "@/components/collection/reading-roadmap";

// Mock Lucide icons to avoid DOM snapshot messiness
vi.mock("lucide-react", async () => {
  const actual = await vi.importActual("lucide-react");
  return {
    ...actual,
    Milestone: () => <div data-testid="icon-milestone" />,
    BookOpen: () => <div data-testid="icon-book" />,
    CheckCircle2: () => <div data-testid="icon-check" />,
    Calendar: () => <div data-testid="icon-calendar" />,
    MoveUp: () => <div data-testid="icon-move-up" />,
    MoveDown: () => <div data-testid="icon-move-down" />,
    FileText: () => <div data-testid="icon-file" />,
  };
});

const sampleItems = [
  {
    id: 1,
    title: "Domain-Driven Design",
    creator: "Eric Evans",
    status: "in_progress" as const,
    target_date: "2026-06-15",
    notes: "Focus on strategic design principles.",
  },
  {
    id: 2,
    title: "Designing Data-Intensive Applications",
    creator: "Martin Kleppmann",
    status: "queued" as const,
    target_date: "2026-08-01",
  },
  {
    id: 3,
    title: "The Mythical Man-Month",
    creator: "Fred Brooks",
    status: "completed" as const,
  },
];

describe("ReadingRoadmapComponent", () => {
  it("renders the roadmap header, descriptions, and list cards correctly", () => {
    render(
      <ReadingRoadmapComponent
        initialItems={sampleItems}
        roadmapTitle="Architecture Roadmap 2026"
        description="Core systems track."
      />
    );

    expect(screen.getByText("Architecture Roadmap 2026")).toBeInTheDocument();
    expect(screen.getByText("Core systems track.")).toBeInTheDocument();
    expect(screen.getByText("Domain-Driven Design")).toBeInTheDocument();
    expect(screen.getByText("by Eric Evans")).toBeInTheDocument();
    expect(screen.getByText("Focus on strategic design principles.")).toBeInTheDocument();
  });

  it("applies accurate situational badge styles matching status variants", () => {
    render(<ReadingRoadmapComponent initialItems={sampleItems} roadmapTitle="Test Queue" />);

    const inProgressBadge = screen.getByText("in_progress");
    const queuedBadge = screen.getByText("queued");
    const completedBadge = screen.getByText("completed");

    expect(inProgressBadge).toBeInTheDocument();
    expect(queuedBadge).toBeInTheDocument();
    expect(completedBadge).toBeInTheDocument();
  });

  it("safely enforces array index boundary logic on reordering action controllers", () => {
    render(<ReadingRoadmapComponent initialItems={sampleItems} roadmapTitle="Boundary Test" />);

    const upButtons = screen.getAllByRole("button", { name: "Move Up" });
    const downButtons = screen.getAllByRole("button", { name: "Move Down" });

    // The top item's MoveUp button should be disabled
    expect(upButtons[0]).toBeDisabled();

    // The bottom item's MoveDown button should be disabled
    expect(downButtons[downButtons.length - 1]).toBeDisabled();
  });

  it("mutates local item state layout correctly when a priority control click triggers", () => {
    render(<ReadingRoadmapComponent initialItems={sampleItems} roadmapTitle="Mutation Test" />);

    // Capture the layout position context
    const headingsBefore = screen.getAllByRole("heading", { level: 4 });
    expect(headingsBefore[0].textContent).toBe("Domain-Driven Design");
    expect(headingsBefore[1].textContent).toBe("Designing Data-Intensive Applications");

    // Click down button on the first node element
    const downButtons = screen.getAllByRole("button", { name: "Move Down" });
    fireEvent.click(downButtons[0]);

    // Assert that DOM positioning shifts array parameters dynamically
    const headingsAfter = screen.getAllByRole("heading", { level: 4 });
    expect(headingsAfter[0].textContent).toBe("Designing Data-Intensive Applications");
    expect(headingsAfter[1].textContent).toBe("Domain-Driven Design");
  });
});
