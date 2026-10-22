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
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { FriendsCard } from "@/components/profile/friends-card";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe("FriendsCard", () => {
  const mockFriendsData = {
    accepted: [
      {
        friendship_id: 1,
        user_id: "user-bob",
        username: "bob",
        display_name: "Bob Builder",
        status: "accepted",
        is_federated: false,
      },
      {
        friendship_id: 2,
        user_id: "user-fed",
        username: "carol@remote.org",
        display_name: "Carol Remote",
        status: "accepted",
        is_federated: true,
        actor_uri: "https://remote.org/users/carol",
      },
    ],
    incoming: [
      {
        friendship_id: 3,
        user_id: "user-dave",
        username: "dave",
        display_name: "Dave Request",
        status: "pending",
        is_federated: false,
      },
    ],
    outgoing: [
      {
        friendship_id: 4,
        user_id: "user-eve",
        username: "eve",
        display_name: "Eve Outgoing",
        status: "pending",
        is_federated: false,
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.get as any).mockResolvedValue({
      data: {
        success: true,
        data: mockFriendsData,
      },
    });
  });

  it("renders accepted friends with local and fediverse badges", async () => {
    render(<FriendsCard />);

    await waitFor(() => {
      expect(screen.getByText("Bob Builder")).toBeInTheDocument();
      expect(screen.getByText("@bob")).toBeInTheDocument();
      expect(screen.getByText("Carol Remote")).toBeInTheDocument();
      expect(screen.getByText("Fediverse")).toBeInTheDocument();
    });
  });

  it("sends a new friend request on submit", async () => {
    (apiClient.post as any).mockResolvedValue({
      data: { success: true },
    });

    render(<FriendsCard />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Username, email/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/Username, email/i);
    fireEvent.change(input, { target: { value: "frank" } });

    const sendBtn = screen.getByRole("button", { name: /Send Request/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/profile/friends/request", {
        identifier: "frank",
      });
    });
  });

  it("switches to incoming tab and allows accepting a request", async () => {
    (apiClient.post as any).mockResolvedValue({
      data: { success: true },
    });

    render(<FriendsCard />);

    await waitFor(() => {
      expect(screen.getByText(/Incoming/i)).toBeInTheDocument();
    });

    const incomingTab = screen.getByText(/Incoming/i);
    fireEvent.click(incomingTab);

    expect(screen.getByText("Dave Request")).toBeInTheDocument();

    const acceptBtn = screen.getByRole("button", { name: /Accept/i });
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith("/profile/friends/3/respond", {
        action: "accept",
      });
    });
  });

  it("removes an accepted friend on remove button click", async () => {
    (apiClient.delete as any).mockResolvedValue({
      data: { success: true },
    });

    render(<FriendsCard />);

    await waitFor(() => {
      expect(screen.getByText("Bob Builder")).toBeInTheDocument();
    });

    const removeBtns = screen.getAllByRole("button", { name: /Remove/i });
    fireEvent.click(removeBtns[0]);

    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith("/profile/friends/1");
    });
  });
});
