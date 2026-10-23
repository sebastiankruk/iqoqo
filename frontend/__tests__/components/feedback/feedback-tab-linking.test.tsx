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
import { render, screen, waitFor } from "@testing-library/react";
import FeedbackPage from "@/app/feedback/page";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(),
}));

vi.mock("@/lib/api/hooks", () => ({
  useProfile: () => ({ data: { id: "test-user-id", roles: ["user"] } }),
}));

vi.mock("@/lib/api/escalations", () => ({
  useMyEscalations: () => ({ data: [] }),
}));

vi.mock("@/components/dashboard/navbar-wrapper", () => ({
  NavbarWithSuspense: () => <div data-testid="mock-navbar" />,
}));

vi.mock("@/components/dashboard/footer", () => ({
  Footer: () => <div data-testid="mock-footer" />,
}));

vi.mock("@/components/escalation/my-escalations", () => ({
  MyEscalations: () => <div data-testid="my-escalations-view">My Escalations Component</div>,
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ data: { data: [], pagination: { page: 1, per_page: 15, total: 0, pages: 1 } } }),
  },
}));

describe("FeedbackPage Tab Linking", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
  });

  it("activates curator escalations tab when tab=my-escalations search param is present", async () => {
    const { useSearchParams } = await import("next/navigation");
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams("tab=my-escalations") as any);

    render(
      <QueryClientProvider client={queryClient}>
        <FeedbackPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId("my-escalations-view")).toBeInTheDocument();
    });
  });

  it("activates platform tickets tab by default when no tab search param is present", async () => {
    const { useSearchParams } = await import("next/navigation");
    vi.mocked(useSearchParams).mockReturnValue(new URLSearchParams() as any);

    render(
      <QueryClientProvider client={queryClient}>
        <FeedbackPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.queryByTestId("my-escalations-view")).not.toBeInTheDocument();
      expect(screen.getByText("Platform Tickets")).toBeInTheDocument();
    });
  });
});
