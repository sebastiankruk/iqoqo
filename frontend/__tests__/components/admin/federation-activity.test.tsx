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
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FederationActivityLog } from "@/components/admin/federation-activity";
import * as federationHooks from "@/lib/api/hooks/federation";
import enMessages from "@/messages/en.json";

vi.mock("next-intl", () => ({
  useLocale: () => "en",
  useTranslations: (namespace?: string) => {
    const dict = namespace === "AdminFederation" ? (enMessages as any).AdminFederation : {};
    return (key: string, values?: Record<string, any>) => {
      let str = dict[key] || key;
      if (values) {
        Object.entries(values).forEach(([k, v]) => {
          str = str.replace(`{${k}}`, String(v));
        });
      }
      return str;
    };
  },
}));

vi.mock("@/lib/api/hooks/federation", () => ({
  useFederationActivities: vi.fn(),
}));

describe("FederationActivityLog Component", () => {
  const mockRefetch = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state when activities are fetching", () => {
    vi.mocked(federationHooks.useFederationActivities).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: mockRefetch,
      isFetching: false,
    } as any);

    render(<FederationActivityLog />);

    expect(screen.getByText("Loading activity pipeline log...")).toBeInTheDocument();
  });

  it("renders empty state when no activities are returned", () => {
    vi.mocked(federationHooks.useFederationActivities).mockReturnValue({
      data: { data: [], pagination: { page: 1, per_page: 20, total: 0, pages: 1 } },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
      isFetching: false,
    } as any);

    render(<FederationActivityLog />);

    expect(screen.getByText("No activity log entries found")).toBeInTheDocument();
  });

  it("renders list of activities with direction, type, and status badges", () => {
    vi.mocked(federationHooks.useFederationActivities).mockReturnValue({
      data: {
        data: [
          {
            id: 1,
            direction: "inbound",
            activity_type: "Create",
            actor_uri: "https://remote.library/users/alice",
            target_uri: "https://local.library/books/123",
            status: "delivered",
            created_at: "2026-10-21T01:00:00Z",
          },
          {
            id: 2,
            direction: "outbound",
            activity_type: "Follow",
            actor_uri: "https://local.library/users/bob",
            target_uri: null,
            status: "failed",
            created_at: "2026-10-21T02:00:00Z",
          },
        ],
        pagination: { page: 1, per_page: 20, total: 2, pages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
      isFetching: false,
    } as any);

    render(<FederationActivityLog />);

    expect(screen.getAllByText("Inbound").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Outbound").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Create").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Follow").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Delivered").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Failed").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("https://remote.library/users/alice")).toBeInTheDocument();
    expect(screen.getByText(/→ https:\/\/local.library\/books\/123/)).toBeInTheDocument();
  });

  it("handles filtering by direction, type, and status", async () => {
    const user = userEvent.setup();
    vi.mocked(federationHooks.useFederationActivities).mockReturnValue({
      data: {
        data: [],
        pagination: { page: 1, per_page: 20, total: 0, pages: 1 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
      isFetching: false,
    } as any);

    render(<FederationActivityLog />);

    const selects = screen.getAllByRole("combobox");
    const directionSelect = selects[0];
    const typeSelect = selects[1];
    const statusSelect = selects[2];

    await user.selectOptions(directionSelect, "inbound");
    expect(federationHooks.useFederationActivities).toHaveBeenLastCalledWith(1, {
      direction: "inbound",
    });

    await user.selectOptions(typeSelect, "Create");
    expect(federationHooks.useFederationActivities).toHaveBeenLastCalledWith(1, {
      direction: "inbound",
      type: "Create",
    });

    await user.selectOptions(statusSelect, "delivered");
    expect(federationHooks.useFederationActivities).toHaveBeenLastCalledWith(1, {
      direction: "inbound",
      type: "Create",
      status: "delivered",
    });
  });

  it("renders pagination controls and navigates between pages", async () => {
    const user = userEvent.setup();
    vi.mocked(federationHooks.useFederationActivities).mockReturnValue({
      data: {
        data: [
          {
            id: 1,
            direction: "inbound",
            activity_type: "Create",
            actor_uri: "https://remote.library/users/alice",
            target_uri: null,
            status: "delivered",
            created_at: "2026-10-21T01:00:00Z",
          },
        ],
        pagination: { page: 1, per_page: 20, total: 35, pages: 2 },
      },
      isLoading: false,
      error: null,
      refetch: mockRefetch,
      isFetching: false,
    } as any);

    render(<FederationActivityLog />);

    expect(screen.getByText("Page 1 of 2 (35 activities)")).toBeInTheDocument();

    const prevBtn = screen.getByLabelText("Previous page");
    const nextBtn = screen.getByLabelText("Next page");

    expect(prevBtn).toBeDisabled();
    expect(nextBtn).toBeEnabled();

    await user.click(nextBtn);
    expect(federationHooks.useFederationActivities).toHaveBeenLastCalledWith(2, {});
  });
});
