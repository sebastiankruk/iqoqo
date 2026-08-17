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
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import FeedbackPage from "@/app/feedback/page";
import { useProfile } from "@/lib/api/hooks";
import { apiClient } from "@/lib/api/client";

// Mock Navbar & Footer to isolate feedback page logic
vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <nav data-testid="mock-navbar">Navbar</nav>,
}));
vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <footer data-testid="mock-footer">Footer</footer>,
}));

vi.mock("@/lib/api/hooks", () => ({
  useProfile: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

const mockTickets = [
  {
    id: 101,
    user_id: "user-1",
    user_display_name: "Alice Reader",
    user_email: "alice@example.com",
    feedback_type: "bug",
    description: "Scan camera is distorted on tablet landscape mode",
    status: "new",
    attachments: ["/static/gallery/shot1.jpg"],
    comments: [],
    comments_count: 0,
    created_at: "2026-08-16T10:00:00Z",
    updated_at: "2026-08-16T10:00:00Z",
  },
  {
    id: 102,
    user_id: "user-2",
    user_display_name: "Bob Collector",
    user_email: "bob@example.com",
    feedback_type: "feature_request",
    description: "Add CSV export button in collection view",
    status: "in_progress",
    attachments: [],
    comments: [
      {
        id: "c1",
        user_id: "admin-1",
        user_display_name: "Admin",
        comment: "Planned for 0.8.0",
        created_at: "2026-08-16T11:00:00Z",
      },
    ],
    comments_count: 1,
    created_at: "2026-08-16T09:00:00Z",
    updated_at: "2026-08-16T11:00:00Z",
  },
];

/**
 * Helper to render components wrapped in a QueryClientProvider for tests.
 *
 * @param {React.ReactElement} ui - The component to render.
 * @returns {ReturnType<typeof render>} Render result.
 */
function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("Feedback Management Page (/feedback)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useProfile).mockReturnValue({
      data: { id: "admin-1", email: "admin@iqoqo.local", roles: ["admin"], permissions: ["tickets:admin"] },
      isLoading: false,
    } as unknown as ReturnType<typeof useProfile>);

    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        data: mockTickets,
        pagination: { page: 1, per_page: 15, total: 2, pages: 1 },
      },
    } as unknown as Awaited<ReturnType<typeof apiClient.get>>);
  });

  it("renders page header and ticket list", async () => {
    renderWithClient(<FeedbackPage />);

    expect(screen.getByText("Help & Feedback")).toBeInTheDocument();
    expect(screen.getByText("Admin View Enabled")).toBeInTheDocument();

    expect(await screen.findByText("Scan camera is distorted on tablet landscape mode")).toBeInTheDocument();
    expect(screen.getByText("Add CSV export button in collection view")).toBeInTheDocument();
    expect(screen.getByText("Alice Reader")).toBeInTheDocument();
    expect(screen.getByText("Bob Collector")).toBeInTheDocument();
  });

  it("filters tickets by keyword search", async () => {
    renderWithClient(<FeedbackPage />);

    await screen.findByText("Scan camera is distorted on tablet landscape mode");

    const searchInput = screen.getByPlaceholderText("Filter by keyword...");
    fireEvent.change(searchInput, { target: { value: "CSV export" } });

    expect(screen.getByText("Add CSV export button in collection view")).toBeInTheDocument();
    expect(screen.queryByText("Scan camera is distorted on tablet landscape mode")).not.toBeInTheDocument();
  });

  it("allows clearing active filters with Reset button", async () => {
    renderWithClient(<FeedbackPage />);

    await screen.findByText("Scan camera is distorted on tablet landscape mode");

    const searchInput = screen.getByPlaceholderText("Filter by keyword...");
    fireEvent.change(searchInput, { target: { value: "nonexistent query" } });

    expect(await screen.findByText("No feedback tickets found")).toBeInTheDocument();

    const resetBtn = screen.getByText("Reset");
    fireEvent.click(resetBtn);

    expect(await screen.findByText("Scan camera is distorted on tablet landscape mode")).toBeInTheDocument();
    expect(screen.getByText("Add CSV export button in collection view")).toBeInTheDocument();
  });

  it("opens ticket detail modal when a card is clicked", async () => {
    renderWithClient(<FeedbackPage />);

    const card = await screen.findByText("Scan camera is distorted on tablet landscape mode");
    fireEvent.click(card);

    expect(await screen.findByText("Ticket #101")).toBeInTheDocument();
  });

  it("opens feedback submission modal on clicking New Request", async () => {
    renderWithClient(<FeedbackPage />);

    const newRequestBtn = screen.getByRole("button", { name: /New Request/i });
    fireEvent.click(newRequestBtn);

    expect(await screen.findByText("Send feedback")).toBeInTheDocument();
  });

  it("sends type and status filters to the API and resets the page", async () => {
    renderWithClient(<FeedbackPage />);
    await screen.findByText("Scan camera is distorted on tablet landscape mode");

    fireEvent.click(screen.getByRole("button", { name: "Bugs" }));
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenLastCalledWith("/feedback", {
        params: { status: undefined, type: "bug", page: 1, per_page: 15 },
      });
    });

    fireEvent.click(screen.getByRole("button", { name: "In Progress" }));
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenLastCalledWith("/feedback", {
        params: { status: "in_progress", type: "bug", page: 1, per_page: 15 },
      });
    });
  });

  it("navigates between API-backed pages", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        data: mockTickets,
        pagination: { page: 1, per_page: 15, total: 31, pages: 3 },
      },
    } as unknown as Awaited<ReturnType<typeof apiClient.get>>);
    renderWithClient(<FeedbackPage />);
    await screen.findByText("Scan camera is distorted on tablet landscape mode");

    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => {
      expect(apiClient.get).toHaveBeenLastCalledWith("/feedback", {
        params: { status: undefined, type: undefined, page: 2, per_page: 15 },
      });
    });
  });
});
