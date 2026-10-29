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
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationCenter } from "@/components/dashboard/notification-center";
import * as notificationsApi from "@/lib/api/notifications";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/lib/api/notifications", async importOriginal => {
  const actual = await importOriginal<typeof notificationsApi>();
  return {
    ...actual,
    useNotifications: vi.fn(),
    useMarkNotificationsRead: vi.fn(),
    useMarkAllNotificationsRead: vi.fn(),
  };
});

describe("NotificationCenter", () => {
  let queryClient: QueryClient;
  const mockMarkRead = vi.fn();
  const mockMarkAllRead = vi.fn();

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
    vi.mocked(notificationsApi.useMarkNotificationsRead).mockReturnValue({
      mutate: mockMarkRead,
      isPending: false,
    } as any);
    vi.mocked(notificationsApi.useMarkAllNotificationsRead).mockReturnValue({
      mutate: mockMarkAllRead,
      isPending: false,
    } as any);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <NotificationCenter enabled={true} />
      </QueryClientProvider>
    );

  it("renders notification bell icon without badge when no unread notifications", () => {
    vi.mocked(notificationsApi.useNotifications).mockReturnValue({
      data: { notifications: [], total: 0, unread_count: 0, limit: 20, offset: 0 },
      isLoading: false,
    } as any);

    renderComponent();
    expect(screen.getByTestId("notification-bell")).toBeInTheDocument();
    expect(screen.queryByTestId("notification-badge")).not.toBeInTheDocument();
  });

  it("renders badge count when unread notifications exist", () => {
    vi.mocked(notificationsApi.useNotifications).mockReturnValue({
      data: {
        notifications: [
          {
            id: 1,
            user_id: "user-1",
            type: "follow_request",
            payload: { message: "Alice followed you" },
            read_at: null,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
        unread_count: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
    } as any);

    renderComponent();
    const badge = screen.getByTestId("notification-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("1");
  });

  it("opens dropdown and displays notification list", async () => {
    const user = userEvent.setup();
    vi.mocked(notificationsApi.useNotifications).mockReturnValue({
      data: {
        notifications: [
          {
            id: 101,
            user_id: "user-1",
            type: "loan_request",
            payload: { message: "Bob requested Dune" },
            read_at: null,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
        unread_count: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
    } as any);

    renderComponent();
    const bell = screen.getByTestId("notification-bell");
    await user.click(bell);

    const heading = await screen.findByText("Notifications");
    expect(heading).toBeInTheDocument();
    expect(screen.getByText("Bob requested Dune")).toBeInTheDocument();
  });

  it("links friend_request notification to /profile?tab=incoming#friends and marks as read on click", async () => {
    const user = userEvent.setup();
    vi.mocked(notificationsApi.useNotifications).mockReturnValue({
      data: {
        notifications: [
          {
            id: 201,
            user_id: "user-1",
            type: "friend_request",
            payload: { message: "Alice sent you a friend request" },
            target_iri: "/profile?tab=incoming#friends",
            read_at: null,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
        unread_count: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
    } as any);

    renderComponent();
    await user.click(screen.getByTestId("notification-bell"));

    const item = await screen.findByText("Alice sent you a friend request");
    expect(item).toBeInTheDocument();

    const link = screen.getByTestId("notification-link-201");
    expect(link).toHaveAttribute("href", "/profile?tab=incoming#friends");

    await user.click(link);
    expect(mockMarkRead).toHaveBeenCalledWith([201]);
  });

  it("links friend_accepted notification to /profile?tab=accepted#friends", async () => {
    const user = userEvent.setup();
    vi.mocked(notificationsApi.useNotifications).mockReturnValue({
      data: {
        notifications: [
          {
            id: 202,
            user_id: "user-1",
            type: "friend_accepted",
            payload: { message: "Bob accepted your friend request" },
            read_at: null,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
        unread_count: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
    } as any);

    renderComponent();
    await user.click(screen.getByTestId("notification-bell"));

    const link = await screen.findByTestId("notification-link-202");
    expect(link).toHaveAttribute("href", "/profile?tab=accepted#friends");
  });

  it("links follow_request notification to /profile?tab=incoming#friends", async () => {
    const user = userEvent.setup();
    vi.mocked(notificationsApi.useNotifications).mockReturnValue({
      data: {
        notifications: [
          {
            id: 203,
            user_id: "user-1",
            type: "follow_request",
            payload: { message: "New friend request from skruk (preview.iqoqo.cc)" },
            read_at: null,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
        unread_count: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
    } as any);

    renderComponent();
    await user.click(screen.getByTestId("notification-bell"));

    const link = await screen.findByTestId("notification-link-203");
    expect(link).toHaveAttribute("href", "/profile?tab=incoming#friends");
  });

  it("renders inline accept and reject buttons for pending follow_request with friendship_id and responds on click", async () => {
    const user = userEvent.setup();
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: { success: true } });
    vi.mocked(notificationsApi.useNotifications).mockReturnValue({
      data: {
        notifications: [
          {
            id: 204,
            user_id: "user-1",
            type: "follow_request",
            payload: {
              message: "New friend request from skruk (preview.iqoqo.cc)",
              friendship_id: "fed:42",
            },
            read_at: null,
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
        unread_count: 1,
        limit: 20,
        offset: 0,
      },
      isLoading: false,
    } as any);

    renderComponent();
    await user.click(screen.getByTestId("notification-bell"));

    const acceptBtn = await screen.findByTestId("notification-accept-204");
    const rejectBtn = screen.getByTestId("notification-reject-204");
    expect(acceptBtn).toBeInTheDocument();
    expect(rejectBtn).toBeInTheDocument();

    await user.click(acceptBtn);
    expect(apiClient.post).toHaveBeenCalledWith("/profile/friends/fed%3A42/respond", { action: "accept" });
    expect(mockMarkRead).toHaveBeenCalledWith([204]);
  });
});
